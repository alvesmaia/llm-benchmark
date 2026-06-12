"""Gerenciamento de conexão com banco de dados SQLite."""

import os
import sqlite3


def get_db_path() -> str:
    return os.environ.get("DB_PATH", "cep.db")


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS localidades (
            loc_nu      INTEGER PRIMARY KEY,
            ufe_sg      TEXT    NOT NULL,
            loc_no      TEXT    NOT NULL,
            cep         TEXT,
            loc_in_sit  TEXT,
            loc_in_tipo TEXT,
            loc_nu_sub  INTEGER,
            loc_no_abrev TEXT,
            mun_nu      TEXT
        );

        CREATE TABLE IF NOT EXISTS bairros (
            bai_nu       INTEGER PRIMARY KEY,
            ufe_sg       TEXT    NOT NULL,
            loc_nu       INTEGER NOT NULL,
            bai_no       TEXT    NOT NULL,
            bai_no_abrev TEXT
        );

        CREATE TABLE IF NOT EXISTS logradouros (
            log_nu        INTEGER PRIMARY KEY,
            ufe_sg        TEXT    NOT NULL,
            loc_nu        INTEGER NOT NULL,
            bai_nu_ini    INTEGER,
            bai_nu_fim    INTEGER,
            log_no        TEXT    NOT NULL,
            log_complemento TEXT,
            cep           TEXT,
            tlo_tx        TEXT,
            log_sta_tlo   TEXT,
            log_no_abrev  TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_localidades_cep  ON localidades(cep)  WHERE cep IS NOT NULL AND cep != '';
        CREATE INDEX IF NOT EXISTS idx_logradouros_cep  ON logradouros(cep)  WHERE cep IS NOT NULL AND cep != '';
        CREATE INDEX IF NOT EXISTS idx_logradouros_loc  ON logradouros(loc_nu);
        CREATE INDEX IF NOT EXISTS idx_bairros_loc      ON bairros(loc_nu);
    """)
    conn.commit()
