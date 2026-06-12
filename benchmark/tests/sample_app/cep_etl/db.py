"""Conexão e schema do banco (SQLite)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def db_path() -> Path:
    return Path(os.environ.get("DB_PATH", "cep.db"))


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path()))
    con.row_factory = sqlite3.Row
    return con


SCHEMA = """
CREATE TABLE IF NOT EXISTS localidade (
    loc_nu INTEGER PRIMARY KEY,
    uf TEXT NOT NULL,
    nome TEXT NOT NULL,
    cep TEXT
);
CREATE TABLE IF NOT EXISTS bairro (
    bai_nu INTEGER PRIMARY KEY,
    uf TEXT NOT NULL,
    loc_nu INTEGER,
    nome TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS logradouro (
    log_nu INTEGER PRIMARY KEY,
    uf TEXT NOT NULL,
    loc_nu INTEGER,
    bai_nu INTEGER,
    nome TEXT NOT NULL,
    complemento TEXT,
    cep TEXT NOT NULL,
    tipo TEXT,
    abrev TEXT
);
CREATE INDEX IF NOT EXISTS idx_logradouro_cep ON logradouro (cep);
CREATE INDEX IF NOT EXISTS idx_localidade_cep ON localidade (cep);
"""


def init_schema(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()
