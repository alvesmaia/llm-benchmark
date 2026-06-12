"""Lógica de estoque: produtos, movimentações (in/out) e dashboard.

Camada de domínio: nenhuma dependência de HTTP/CLI. Estoque nunca fica negativo.
"""

from __future__ import annotations

import sqlite3
from math import floor


class StockError(ValueError):
    """Erro de regra de estoque (ex.: saída maior que o saldo)."""


def import_cost(price: float) -> int:
    """Convenção determinística de custo de uma venda importada: floor(0.8 * price)."""
    return floor(0.8 * float(price))


def upsert_product(con: sqlite3.Connection, company: str, model: str,
                   unit_cost: int = 0) -> int:
    """Cria (ou recupera) o produto por (company, model). Retorna o id."""
    row = con.execute(
        "SELECT id FROM products WHERE company = ? AND model = ?", (company, model)).fetchone()
    if row is not None:
        return int(row["id"])
    cur = con.execute(
        "INSERT INTO products (company, model, unit_cost, stock) VALUES (?, ?, ?, 0)",
        (company, model, int(unit_cost)),
    )
    return int(cur.lastrowid)


def list_products(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute(
        "SELECT id, company, model, stock, unit_cost FROM products ORDER BY id").fetchall()
    return [
        {"id": r["id"], "company": r["company"], "model": r["model"],
         "stock": r["stock"], "unit_cost": r["unit_cost"]}
        for r in rows
    ]


def get_product(con: sqlite3.Connection, product_id: int) -> dict | None:
    r = con.execute(
        "SELECT id, company, model, stock, unit_cost FROM products WHERE id = ?",
        (product_id,)).fetchone()
    if r is None:
        return None
    return {"id": r["id"], "company": r["company"], "model": r["model"],
            "stock": r["stock"], "unit_cost": r["unit_cost"]}


def register_movement(con: sqlite3.Connection, product_id: int, mtype: str, qty: int,
                      *, unit_price: int = 0, unit_cost: int = 0, region: str | None = None,
                      source: str = "manual", external_id: str | None = None) -> dict:
    """Registra uma movimentação e atualiza o saldo. 'out' maior que o estoque => StockError."""
    if mtype not in ("in", "out"):
        raise StockError(f"tipo inválido: {mtype!r} (use 'in' ou 'out')")
    if qty <= 0:
        raise StockError("qty deve ser positivo")

    prod = con.execute("SELECT stock FROM products WHERE id = ?", (product_id,)).fetchone()
    if prod is None:
        raise StockError(f"produto inexistente: {product_id}")

    delta = qty if mtype == "in" else -qty
    new_stock = prod["stock"] + delta
    if new_stock < 0:
        raise StockError(
            f"saída ({qty}) maior que o estoque atual ({prod['stock']})")

    con.execute(
        """INSERT INTO movements
           (product_id, type, qty, unit_price, unit_cost, region, source, external_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (product_id, mtype, qty, int(unit_price), int(unit_cost), region, source, external_id),
    )
    con.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
    con.commit()
    return {"product_id": product_id, "type": mtype, "qty": qty, "stock": new_stock}


def dashboard(con: sqlite3.Connection) -> dict:
    """Agrega métricas das movimentações.

    revenue = soma dos unit_price das saídas (out)
    cost    = soma dos unit_cost das saídas importadas + custos das entradas (in)
    units_sold = nº de saídas; movements = total de movimentações
    """
    revenue = con.execute(
        "SELECT COALESCE(SUM(unit_price * qty), 0) FROM movements WHERE type = 'out'"
    ).fetchone()[0]
    cost = con.execute(
        "SELECT COALESCE(SUM(unit_cost * qty), 0) FROM movements WHERE unit_cost > 0"
    ).fetchone()[0]
    units_sold = con.execute(
        "SELECT COALESCE(SUM(qty), 0) FROM movements WHERE type = 'out'"
    ).fetchone()[0]
    movements = con.execute("SELECT COUNT(*) FROM movements").fetchone()[0]

    by_company: dict[str, int] = {}
    for r in con.execute(
        """SELECT p.company AS company, COALESCE(SUM(m.unit_price * m.qty), 0) AS rev
           FROM movements m JOIN products p ON p.id = m.product_id
           WHERE m.type = 'out' GROUP BY p.company"""
    ).fetchall():
        by_company[r["company"]] = r["rev"]

    by_region: dict[str, int] = {}
    for r in con.execute(
        """SELECT region, COALESCE(SUM(unit_price * qty), 0) AS rev
           FROM movements WHERE type = 'out' AND region IS NOT NULL AND region != ''
           GROUP BY region"""
    ).fetchall():
        by_region[r["region"]] = r["rev"]

    return {
        "revenue": revenue,
        "cost": cost,
        "profit": revenue - cost,
        "units_sold": units_sold,
        "movements": movements,
        "by_company": by_company,
        "by_region": by_region,
    }
