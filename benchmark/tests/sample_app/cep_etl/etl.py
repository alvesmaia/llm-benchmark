"""ETL: lê os arquivos eDNE Básico (delimitados por @, Latin-1) e carrega no banco."""

from __future__ import annotations

import os
from pathlib import Path

from cep_etl.db import connect, init_schema

ENCODING = "latin-1"
SEP = "@"


class DneError(Exception):
    """Erro acionável relacionado à base DNE."""


def _dne_dir() -> Path:
    raw = os.environ.get("DNE_PATH")
    if not raw:
        raise DneError(
            "Variável DNE_PATH não definida. Aponte para a pasta com os arquivos LOG_*.TXT.")
    path = Path(raw)
    if not path.exists():
        raise DneError(f"DNE_PATH não existe: {path}")
    return path


def _read_rows(path: Path) -> list[list[str]]:
    rows = []
    for line in path.read_text(encoding=ENCODING).splitlines():
        if line.strip():
            rows.append(line.split(SEP))
    return rows


def _to_int(value: str) -> int | None:
    value = (value or "").strip()
    return int(value) if value.isdigit() else None


def _clean_cep(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def load() -> dict:
    """Carga idempotente: usa INSERT OR REPLACE por PK, então recarregar não duplica."""
    dne = _dne_dir()

    loc_file = dne / "LOG_LOCALIDADE.TXT"
    if not loc_file.exists():
        raise DneError(f"Arquivo obrigatório ausente: {loc_file.name} em {dne}")

    con = connect()
    init_schema(con)
    counts = {"localidade": 0, "bairro": 0, "logradouro": 0}

    # localidades
    for r in _read_rows(loc_file):
        loc_nu = _to_int(r[0])
        if loc_nu is None:
            continue
        con.execute(
            "INSERT OR REPLACE INTO localidade (loc_nu, uf, nome, cep) VALUES (?, ?, ?, ?)",
            (loc_nu, r[1].strip(), r[2].strip(), _clean_cep(r[3]) or None),
        )
        counts["localidade"] += 1

    # bairros (opcional)
    bai_file = dne / "LOG_BAIRRO.TXT"
    if bai_file.exists():
        for r in _read_rows(bai_file):
            bai_nu = _to_int(r[0])
            if bai_nu is None:
                continue
            con.execute(
                "INSERT OR REPLACE INTO bairro (bai_nu, uf, loc_nu, nome) VALUES (?, ?, ?, ?)",
                (bai_nu, r[1].strip(), _to_int(r[2]), r[3].strip()),
            )
            counts["bairro"] += 1

    # logradouros (um arquivo por UF)
    for log_file in sorted(dne.glob("LOG_LOGRADOURO_*.TXT")):
        for r in _read_rows(log_file):
            log_nu = _to_int(r[0])
            if log_nu is None:
                continue
            con.execute(
                """INSERT OR REPLACE INTO logradouro
                   (log_nu, uf, loc_nu, bai_nu, nome, complemento, cep, tipo, abrev)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    log_nu, r[1].strip(), _to_int(r[2]), _to_int(r[3]),
                    r[5].strip(), (r[6].strip() or None), _clean_cep(r[7]),
                    r[8].strip() if len(r) > 8 else None,
                    r[10].strip() if len(r) > 10 else None,
                ),
            )
            counts["logradouro"] += 1

    con.commit()
    con.close()
    return counts
