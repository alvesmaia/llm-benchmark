"""Testes do módulo ETL."""


import pytest

from cep_etl.db import get_connection, init_schema
from cep_etl.etl import run_etl


def test_init_schema_creates_tables(tmp_db):
    conn = get_connection(tmp_db)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "localidades" in tables
        assert "bairros" in tables
        assert "logradouros" in tables
    finally:
        conn.close()


def test_init_schema_creates_indexes(tmp_db):
    conn = get_connection(tmp_db)
    try:
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        assert "idx_localidades_cep" in indexes
        assert "idx_logradouros_cep" in indexes
    finally:
        conn.close()


def test_init_schema_idempotent(tmp_db):
    """Rodar init_schema duas vezes não deve causar erro."""
    conn = get_connection(tmp_db)
    try:
        init_schema(conn)  # segunda chamada
        init_schema(conn)  # terceira chamada — deve ser idempotente
    finally:
        conn.close()


def test_etl_missing_dne_path(tmp_path, monkeypatch):
    monkeypatch.delenv("DNE_PATH", raising=False)
    with pytest.raises(EnvironmentError, match="DNE_PATH"):
        run_etl(db_path=str(tmp_path / "test.db"))


def test_etl_invalid_dne_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_etl(dne_path=str(tmp_path / "nao_existe"), db_path=str(tmp_path / "test.db"))


def test_etl_missing_required_files(tmp_path):
    """Pasta existe mas sem os arquivos obrigatórios."""
    dne_dir = tmp_path / "dne"
    dne_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="obrigatórios"):
        run_etl(dne_path=str(dne_dir), db_path=str(tmp_path / "test.db"))


def test_etl_integration(dne_sample_path, tmp_path):
    """Teste de integração: carrega a amostra real do DNE."""
    db_path = str(tmp_path / "cep.db")
    counts = run_etl(dne_path=dne_sample_path, db_path=db_path)

    assert counts["localidades"] > 0
    assert counts["bairros"] > 0
    assert counts["logradouros"] > 0

    conn = get_connection(db_path)
    try:
        n_loc = conn.execute("SELECT COUNT(*) FROM localidades").fetchone()[0]
        n_bai = conn.execute("SELECT COUNT(*) FROM bairros").fetchone()[0]
        n_log = conn.execute("SELECT COUNT(*) FROM logradouros").fetchone()[0]
        assert n_loc == counts["localidades"]
        assert n_bai == counts["bairros"]
        assert n_log == counts["logradouros"]
    finally:
        conn.close()


def test_etl_idempotent(dne_sample_path, tmp_path):
    """Rodar ETL duas vezes não duplica dados."""
    db_path = str(tmp_path / "cep.db")
    c1 = run_etl(dne_path=dne_sample_path, db_path=db_path)
    c2 = run_etl(dne_path=dne_sample_path, db_path=db_path)
    assert c1 == c2

    conn = get_connection(db_path)
    try:
        n_log = conn.execute("SELECT COUNT(*) FROM logradouros").fetchone()[0]
        assert n_log == c1["logradouros"]
    finally:
        conn.close()
