"""Conexão e schema do banco (SQLite). Camada de persistência."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def db_path() -> Path:
    return Path(os.environ.get("DB_PATH", "inventory.db"))


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path()))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    model TEXT NOT NULL,
    unit_cost INTEGER NOT NULL DEFAULT 0,
    stock INTEGER NOT NULL DEFAULT 0,
    UNIQUE (company, model)
);
CREATE TABLE IF NOT EXISTS movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('in', 'out')),
    qty INTEGER NOT NULL,
    unit_price INTEGER NOT NULL DEFAULT 0,
    unit_cost INTEGER NOT NULL DEFAULT 0,
    region TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    external_id TEXT,
    FOREIGN KEY (product_id) REFERENCES products (id)
);
CREATE INDEX IF NOT EXISTS idx_products_company_model ON products (company, model);
CREATE INDEX IF NOT EXISTS idx_movements_product ON movements (product_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_movements_external ON movements (external_id)
    WHERE external_id IS NOT NULL;
"""


def init_schema(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()
