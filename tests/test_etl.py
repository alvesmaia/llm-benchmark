"""Testes do módulo ETL."""


import pytest

from cep_etl.db import get_connection
from cep_etl.etl import run_etl


def test_etl_carga_completa(dne_path, db_path):
    """ETL carrega localidades, bairros e logradouros corretamente."""
    result = run_etl(db_path=db_path, dne_path=dne_path)
    assert result["localidades"] == 4
    assert result["bairros"] == 4
    assert result["logradouros"] == 4


def test_etl_idempotente(dne_path, db_path):
    """Rodar o ETL duas vezes não duplica dados."""
    run_etl(db_path=db_path, dne_path=dne_path)
    run_etl(db_path=db_path, dne_path=dne_path)

    conn = get_connection(db_path)
    n_loc = conn.execute("SELECT COUNT(*) FROM localidade").fetchone()[0]
    n_bai = conn.execute("SELECT COUNT(*) FROM bairro").fetchone()[0]
    n_log = conn.execute("SELECT COUNT(*) FROM logradouro").fetchone()[0]
    conn.close()

    assert n_loc == 4
    assert n_bai == 4
    assert n_log == 4


def test_etl_sem_dne_path(db_path, monkeypatch):
    """ETL levanta RuntimeError quando DNE_PATH não está definido."""
    monkeypatch.delenv("DNE_PATH", raising=False)
    with pytest.raises(RuntimeError, match="DNE_PATH"):
        run_etl(db_path=db_path)


def test_etl_dne_path_invalido(db_path):
    """ETL levanta RuntimeError quando o diretório não existe."""
    with pytest.raises(RuntimeError):
        run_etl(db_path=db_path, dne_path="/caminho/que/nao/existe")


def test_etl_sem_arquivo_logradouro(tmp_path, db_path):
    """ETL levanta RuntimeError quando não há arquivos LOG_LOGRADOURO_*.TXT."""
    (tmp_path / "LOG_LOCALIDADE.TXT").write_text(
        "1@SP@São Paulo@@0@0@@S.Paulo@3550308\n", encoding="latin-1"
    )
    (tmp_path / "LOG_BAIRRO.TXT").write_text(
        "1@SP@1@Sé@Sé\n", encoding="latin-1"
    )
    with pytest.raises(RuntimeError, match="LOG_LOGRADOURO"):
        run_etl(db_path=db_path, dne_path=str(tmp_path))


def test_etl_cria_indices(dne_path, db_path):
    """ETL cria índices em CEP."""
    run_etl(db_path=db_path, dne_path=dne_path)
    conn = get_connection(db_path)
    indices = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%cep%'"
    ).fetchall()
    conn.close()
    names = [r[0] for r in indices]
    assert any("logradouro" in n for n in names)
    assert any("localidade" in n for n in names)
