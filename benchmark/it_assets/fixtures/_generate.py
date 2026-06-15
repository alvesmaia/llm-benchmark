"""Gera a fixture sintética do cenário `it_assets` (movimentação de ativos de TI).

Rodar: PYTHONIOENCODING=utf-8 uv run --python 3.12 python benchmark/it_assets/fixtures/_generate.py

Cria um CSV pequeno e determinístico de **movimentações de ativos de TI** e grava um `expected.json`
mínimo (só o suficiente para a checagem "usa a base": nº de linhas, ações válidas e o conjunto de
asset_tags). O CSV é **gitignored** — só este `_generate.py` (+ `expected.json`) são versionados.

Também expõe `perturb_dataset(app_dir)`: a perturbação dirigida da Fase 3, que muta valores no CSV já
copiado para `<app>/data/` (campos nulos, ação fora do domínio, valor negativo, data alternativa,
movement_id duplicado), preservando o cabeçalho.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

FIX_DIR = Path(__file__).parent
CSV_PATH = FIX_DIR / "it_assets_movements" / "movements.csv"
EXPECTED_PATH = FIX_DIR / "expected.json"

HEADER = [
    "movement_id", "date", "asset_tag", "asset_type", "action",
    "employee", "from_location", "to_location", "status", "value",
]

VALID_ACTIONS = ["allocate", "return", "transfer", "maintenance"]

# Movimentações sintéticas com acentos/edge propositais. Determinístico.
# Campos por linha: date, asset_tag, asset_type, action, employee, from_loc, to_loc, status, value
_RAW = [
    ["2024-01-03", "NB-0001", "notebook", "allocate", "José Antônio", "Almoxarifado", "TI - 3º andar", "in_use", "5200.00"],
    ["2024-01-05", "NB-0002", "notebook", "allocate", "Maria Conceição", "Almoxarifado", "Vendas", "in_use", "4800.00"],
    ["2024-01-08", "MON-0101", "monitor", "allocate", "João da Silva", "Almoxarifado", "Vendas", "in_use", "1200.00"],
    ["2024-01-10", "NB-0003", "notebook", "transfer", "Ana Paula", "TI - 3º andar", "Diretoria", "in_use", "6100.00"],
    ["2024-01-12", "PH-0201", "phone", "allocate", "Carlos Eduardo", "Almoxarifado", "Logística", "in_use", "3300.00"],
    ["2024-01-15", "NB-0001", "maintenance", "maintenance", "", "TI - 3º andar", "Assistência", "in_repair", "250.00"],
    ["2024-01-18", "MON-0102", "monitor", "allocate", "Beatriz Lação", "Almoxarifado", "Financeiro", "in_use", "1150.00"],
    ["2024-01-20", "NB-0004", "notebook", "allocate", "Rafael Gonçalves", "Almoxarifado", "Engenharia", "in_use", "7200.00"],
    ["2024-01-22", "PH-0202", "phone", "allocate", "Fernanda Müller", "Almoxarifado", "RH", "in_use", "2900.00"],
    ["2024-01-25", "NB-0002", "return", "return", "Maria Conceição", "Vendas", "Almoxarifado", "available", "4800.00"],
    ["2024-01-28", "TB-0301", "tablet", "allocate", "Lucas Almeida", "Almoxarifado", "Vendas", "in_use", "2100.00"],
    ["2024-02-01", "NB-0005", "notebook", "allocate", "Patrícia Nóbrega", "Almoxarifado", "Marketing", "in_use", "5600.00"],
    ["2024-02-03", "MON-0101", "monitor", "transfer", "Thiago Ávila", "Vendas", "Marketing", "in_use", "1200.00"],
    ["2024-02-06", "NB-0001", "return", "return", "", "Assistência", "Almoxarifado", "available", "5200.00"],
    ["2024-02-09", "PH-0203", "phone", "allocate", "Juliana Rezende", "Almoxarifado", "Diretoria", "in_use", "3100.00"],
    ["2024-02-11", "NB-0006", "notebook", "allocate", "Marcelo Fróes", "Almoxarifado", "Suporte", "in_use", "4500.00"],
    ["2024-02-14", "TB-0302", "tablet", "allocate", "Camila Sá", "Almoxarifado", "Comercial", "in_use", "1980.00"],
    ["2024-02-17", "NB-0003", "maintenance", "maintenance", "Ana Paula", "Diretoria", "Assistência", "in_repair", "320.00"],
    ["2024-02-20", "MON-0103", "monitor", "allocate", "Renato Lima", "Almoxarifado", "Engenharia", "in_use", "1300.00"],
    ["2024-02-23", "NB-0004", "transfer", "transfer", "Rafael Gonçalves", "Engenharia", "Suporte", "in_use", "7200.00"],
    ["2024-02-26", "PH-0201", "phone", "return", "Carlos Eduardo", "Logística", "Almoxarifado", "available", "3300.00"],
    ["2024-03-01", "NB-0007", "notebook", "allocate", "Vanessa Côrtes", "Almoxarifado", "Financeiro", "in_use", "5900.00"],
    ["2024-03-04", "TB-0301", "tablet", "maintenance", "Lucas Almeida", "Vendas", "Assistência", "in_repair", "180.00"],
    ["2024-03-07", "NB-0008", "notebook", "allocate", "Eduardo Peçanha", "Almoxarifado", "TI - 3º andar", "in_use", "6800.00"],
    ["2024-03-10", "MON-0102", "monitor", "transfer", "Beatriz Lação", "Financeiro", "RH", "in_use", "1150.00"],
    ["2024-03-13", "PH-0202", "phone", "return", "Fernanda Müller", "RH", "Almoxarifado", "available", "2900.00"],
    ["2024-03-16", "NB-0005", "transfer", "transfer", "Patrícia Nóbrega", "Marketing", "Vendas", "in_use", "5600.00"],
    ["2024-03-19", "TB-0303", "tablet", "allocate", "Sérgio Antunes", "Almoxarifado", "Logística", "in_use", "2050.00"],
    ["2024-03-22", "NB-0009", "notebook", "allocate", "Letícia Brandão", "Almoxarifado", "Comercial", "in_use", "5300.00"],
    ["2024-03-25", "MON-0101", "monitor", "return", "Thiago Ávila", "Marketing", "Almoxarifado", "available", "1200.00"],
]


def _rows() -> list[list[str]]:
    rows = []
    for i, r in enumerate(_RAW, start=1):
        rows.append([f"MV-{i:04d}", *r])
    return rows


def _expected(rows: list[list[str]]) -> dict:
    col = {name: idx for idx, name in enumerate(HEADER)}
    tags = sorted({r[col["asset_tag"]] for r in rows})
    actions = sorted({r[col["action"]] for r in rows})
    return {
        "row_count": len(rows),
        "valid_actions": VALID_ACTIONS,
        "actions_in_dataset": actions,
        "asset_tags": tags,
        "asset_tags_count": len(tags),
    }


def main() -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = _rows()
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)
    expected = _expected(rows)
    EXPECTED_PATH.write_text(json.dumps(expected, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"CSV gerado em {CSV_PATH} ({len(rows)} movimentações)")
    print(f"expected.json gerado em {EXPECTED_PATH}")
    print(json.dumps(expected, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Perturbação dirigida da Fase 3
# ---------------------------------------------------------------------------
def _find_dataset_csv(app_dir: Path) -> Path | None:
    """Localiza o CSV copiado em <app>/data/ (qualquer .csv). Fallback: None."""
    data_dir = app_dir / "data"
    if data_dir.exists():
        csvs = sorted(data_dir.rglob("*.csv"))
        if csvs:
            # prefere o maior (a base copiada, não algum artefato menor)
            return max(csvs, key=lambda p: p.stat().st_size)
    # fallback: qualquer .csv no projeto (exceto venv)
    csvs = [p for p in app_dir.rglob("*.csv") if ".venv" not in p.parts]
    if csvs:
        return max(csvs, key=lambda p: p.stat().st_size)
    return None


def perturb_dataset(app_dir: Path) -> dict:
    """Muta valores no CSV copiado dentro do projeto, ANTES da Fase 3. Determinístico, preserva o
    cabeçalho. Injeta: campos obrigatórios vazios, ação fora do domínio, valor negativo, data em
    formato alternativo e movement_id duplicado. Retorna um resumo (também útil em testes)."""
    csv_path = _find_dataset_csv(app_dir)
    if csv_path is None:
        return {"perturbed": False, "warning": "CSV não encontrado em <app>/data/ (hook ignorado)"}

    with csv_path.open("r", newline="", encoding="utf-8", errors="replace") as f:
        reader = list(csv.reader(f))
    if len(reader) < 2:
        return {"perturbed": False, "warning": "CSV sem linhas de dados"}

    header = reader[0]
    body = reader[1:]
    idx = {name: i for i, name in enumerate(header)}
    applied = []

    # 1. esvazia campos obrigatórios em algumas linhas
    if "employee" in idx and len(body) > 2:
        body[2][idx["employee"]] = ""
        applied.append("employee vazio (linha 3)")
    if "value" in idx and len(body) > 3:
        body[3][idx["value"]] = ""
        applied.append("value vazio (linha 4)")

    # 2. ação fora do domínio
    if "action" in idx and len(body) > 4:
        body[4][idx["action"]] = "decommission_xyz"
        applied.append("action fora do domínio (linha 5)")

    # 3. valor negativo
    if "value" in idx and len(body) > 5:
        body[5][idx["value"]] = "-999.99"
        applied.append("value negativo (linha 6)")

    # 4. data em formato alternativo (dd/mm/yyyy em vez de ISO)
    if "date" in idx and len(body) > 6:
        body[6][idx["date"]] = "15/03/2024"
        applied.append("data em formato alternativo (linha 7)")

    # 5. movement_id duplicado
    if "movement_id" in idx and len(body) > 7:
        body[7][idx["movement_id"]] = body[0][idx["movement_id"]]
        applied.append("movement_id duplicado (linha 8)")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(body)

    return {"perturbed": True, "csv": str(csv_path), "mutations": applied}


if __name__ == "__main__":
    main()
