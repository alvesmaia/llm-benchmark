"""Gerenciamento de conexão e schema do banco de dados."""

import os
import sqlite3
from contextlib import contextmanager

DEFAULT_DB_PATH = "cep.db"


def get_db_path() -> str:
    return os.environ.get("DB_PATH", DEFAULT_DB_PATH)


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


@contextmanager
def db_connection(db_path: str | None = None):
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


DDL = """
CREATE TABLE IF NOT EXISTS localidade (
    loc_nu      INTEGER PRIMARY KEY,
    ufe_sg      TEXT NOT NULL,
    loc_no      TEXT NOT NULL,
    cep         TEXT,
    loc_in_sit  TEXT,
    loc_in_tipo TEXT,
    loc_nu_sub  INTEGER,
    loc_no_abrev TEXT,
    mun_nu      TEXT
);

CREATE TABLE IF NOT EXISTS bairro (
    bai_nu      INTEGER PRIMARY KEY,
    ufe_sg      TEXT NOT NULL,
    loc_nu      INTEGER NOT NULL,
    bai_no      TEXT NOT NULL,
    bai_no_abrev TEXT,
    FOREIGN KEY (loc_nu) REFERENCES localidade(loc_nu)
);

CREATE TABLE IF NOT EXISTS logradouro (
    log_nu          INTEGER PRIMARY KEY,
    ufe_sg          TEXT NOT NULL,
    loc_nu          INTEGER NOT NULL,
    bai_nu_ini      INTEGER,
    bai_nu_fim      INTEGER,
    log_no          TEXT NOT NULL,
    log_complemento TEXT,
    cep             TEXT NOT NULL,
    tlo_tx          TEXT,
    log_sta_tlo     TEXT,
    log_no_abrev    TEXT,
    FOREIGN KEY (loc_nu) REFERENCES localidade(loc_nu),
    FOREIGN KEY (bai_nu_ini) REFERENCES bairro(bai_nu)
);

CREATE INDEX IF NOT EXISTS idx_logradouro_cep ON logradouro(cep);
CREATE INDEX IF NOT EXISTS idx_localidade_cep ON localidade(cep);
"""


def create_schema(conn: sqlite3.Connection) -> None:
    for statement in DDL.strip().split(";"):
        stmt = statement.strip()
        if stmt:
            conn.execute(stmt)
    conn.commit()
