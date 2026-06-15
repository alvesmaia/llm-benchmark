"""Ingestão robusta do CSV de movimentações para o SQLite.

Tolerante a dados sujos (perturbação da Fase 3): campos nulos/vazios, ações fora do domínio,
valores negativos, datas em formato alternativo e movement_id duplicado. Nada disso derruba a
carga — valores inválidos são normalizados/saneados e a linha é mantida quando possível.
"""

from __future__ import annotations

import csv
import sqlite3
from datetime import datetime

from it_assets.config import settings
from it_assets.db import connect, init_db, seed_users

VALID_ACTIONS = {"allocate", "return", "transfer", "maintenance"}

# mapeamento tolerante do cabeçalho -> coluna canônica
_ALIASES = {
    "movement_id": ["movement_id", "id", "mov_id"],
    "date": ["date", "data", "movement_date"],
    "asset_tag": ["asset_tag", "tag", "asset", "patrimonio"],
    "asset_type": ["asset_type", "type", "tipo"],
    "action": ["action", "acao", "movimento"],
    "employee": ["employee", "colaborador", "user"],
    "from_location": ["from_location", "from", "origem"],
    "to_location": ["to_location", "to", "destino"],
    "status": ["status", "situacao"],
    "value": ["value", "valor", "price", "cost"],
}


def _column_map(header: list[str]) -> dict[str, int]:
    lower = {h.strip().lower(): i for i, h in enumerate(header)}
    out: dict[str, int] = {}
    for canon, names in _ALIASES.items():
        for name in names:
            if name in lower:
                out[canon] = lower[name]
                break
    return out


def _parse_value(raw: str | None) -> float | None:
    """Valor numérico saneado: vazio/nulo -> None; negativo -> 0.0 (não há valor negativo)."""
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        v = float(raw.replace(",", "."))
    except ValueError:
        return None
    return max(0.0, v)


def _parse_date(raw: str | None) -> str | None:
    """Aceita ISO e formatos alternativos (DD/MM/YYYY, MM/DD/YYYY); inválido/vazio -> None."""
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _norm_action(raw: str | None) -> str:
    """Ação normalizada; fora do domínio vira 'other' (mantém a linha, não quebra)."""
    a = (raw or "").strip().lower()
    return a if a in VALID_ACTIONS else "other"


def load_csv(con: sqlite3.Connection, dataset_path: str | None = None) -> int:
    """Carga idempotente: limpa movimentações e recarrega. Retorna nº de linhas inseridas."""
    path = dataset_path or settings.dataset_path
    con.execute("DELETE FROM movements")
    inserted = 0
    seen_ids: set[str] = set()
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        con.commit()
        return 0
    header, body = rows[0], rows[1:]
    cmap = _column_map(header)

    def cell(row: list[str], canon: str) -> str | None:
        i = cmap.get(canon)
        if i is None or i >= len(row):
            return None
        return row[i]

    for row in body:
        if not any((c or "").strip() for c in row):
            continue  # linha totalmente vazia
        asset_tag = (cell(row, "asset_tag") or "").strip()
        if not asset_tag:
            continue  # sem ativo: não há o que registrar
        mov_id = (cell(row, "movement_id") or "").strip() or None
        # movement_id duplicado: mantém o registro mas anula o id duplicado p/ não violar suposições
        if mov_id and mov_id in seen_ids:
            mov_id = None
        if mov_id:
            seen_ids.add(mov_id)
        con.execute(
            """INSERT INTO movements
               (movement_id, date, asset_tag, asset_type, action, employee,
                from_location, to_location, status, value)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mov_id,
                _parse_date(cell(row, "date")),
                asset_tag,
                (cell(row, "asset_type") or "").strip() or None,
                _norm_action(cell(row, "action")),
                (cell(row, "employee") or "").strip() or None,
                (cell(row, "from_location") or "").strip() or None,
                (cell(row, "to_location") or "").strip() or None,
                (cell(row, "status") or "").strip() or None,
                _parse_value(cell(row, "value")),
            ),
        )
        inserted += 1
    con.commit()
    return inserted


def ensure_loaded(db_path: str | None = None, dataset_path: str | None = None) -> int:
    """Inicializa o schema, semeia usuários e carrega o CSV. Retorna nº de movimentações."""
    con = connect(db_path)
    try:
        init_db(con)
        seed_users(con)
        n = load_csv(con, dataset_path)
        return n
    finally:
        con.close()
