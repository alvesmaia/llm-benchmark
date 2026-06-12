"""ETL: lê o CSV de vendas (schema car-sales) e popula produtos + movimentações de saída.

Cada linha do CSV é UMA venda (saída). Produto = par (Company, Model). A importação é idempotente:
o `Car_id` de cada linha vira o `external_id` da movimentação; reimportar não duplica.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

from inv_etl.db import connect, init_schema
from inv_etl.inventory import import_cost, upsert_product

# Colunas relevantes do schema Kaggle car-sales-report.
COL_CAR_ID = "Car_id"
COL_COMPANY = "Company"
COL_MODEL = "Model"
COL_PRICE = "Price ($)"
COL_REGION = "Dealer_Region"


class DatasetError(Exception):
    """Erro acionável relacionado ao dataset CSV."""


def _dataset_path() -> Path:
    raw = os.environ.get("DATASET_PATH")
    if not raw:
        raise DatasetError(
            "Variável DATASET_PATH não definida. Aponte para o CSV de vendas (car-sales).")
    path = Path(raw)
    if not path.exists():
        raise DatasetError(f"DATASET_PATH não existe: {path}")
    return path


def _to_price(value: str) -> int:
    try:
        return int(float((value or "0").strip()))
    except ValueError as e:
        raise DatasetError(f"preço inválido: {value!r}") from e


def import_sales() -> dict:
    """Importação idempotente: upsert de produtos + uma movimentação OUT por venda."""
    path = _dataset_path()

    con = connect()
    init_schema(con)
    counts = {"products": 0, "movements": 0, "skipped": 0}
    products_seen: set[int] = set()

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {COL_CAR_ID, COL_COMPANY, COL_MODEL, COL_PRICE, COL_REGION}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            missing = required - set(reader.fieldnames or [])
            raise DatasetError(f"colunas obrigatórias ausentes no CSV: {sorted(missing)}")

        for row in reader:
            company = (row.get(COL_COMPANY) or "").strip()
            model = (row.get(COL_MODEL) or "").strip()
            if not company or not model:
                counts["skipped"] += 1
                continue
            price = _to_price(row.get(COL_PRICE, "0"))
            region = (row.get(COL_REGION) or "").strip() or None
            car_id = (row.get(COL_CAR_ID) or "").strip() or None

            cost = import_cost(price)
            pid = upsert_product(con, company, model, unit_cost=cost)
            if pid not in products_seen:
                products_seen.add(pid)
                counts["products"] += 1

            # idempotência: se já existe movimentação com este external_id, pula.
            if car_id is not None:
                existing = con.execute(
                    "SELECT 1 FROM movements WHERE external_id = ?", (car_id,)).fetchone()
                if existing is not None:
                    counts["skipped"] += 1
                    continue

            # Movimentação de import (OUT) é histórica: NÃO impõe saldo nem atualiza stock.
            con.execute(
                """INSERT INTO movements
                   (product_id, type, qty, unit_price, unit_cost, region, source, external_id)
                   VALUES (?, 'out', 1, ?, ?, ?, 'import', ?)""",
                (pid, price, cost, region, car_id),
            )
            counts["movements"] += 1

    con.commit()
    con.close()
    return counts
