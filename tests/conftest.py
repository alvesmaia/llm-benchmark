"""Fixtures compartilhadas entre os testes."""

import os
from pathlib import Path

import pytest

from cep_etl.db import get_connection, init_schema


@pytest.fixture
def tmp_db(tmp_path):
    """Banco SQLite temporário com schema inicializado."""
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    init_schema(conn)
    conn.close()
    return db_path


@pytest.fixture
def populated_db(tmp_db):
    """Banco com dados de exemplo para testes de consulta."""
    conn = get_connection(tmp_db)
    conn.executemany(
        "INSERT INTO localidades (loc_nu, ufe_sg, loc_no, cep, loc_in_sit, loc_in_tipo, loc_nu_sub, loc_no_abrev, mun_nu) VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (1, "SP", "São Paulo", None, "0", "0", None, "S.Paulo", "3550308"),
            (2, "RJ", "Rio de Janeiro", None, "0", "0", None, "R.Janeiro", "3304557"),
            (99, "SP", "Município Teste", "99999000", "0", "0", None, "Mun.Teste", "9999999"),
        ],
    )
    conn.executemany(
        "INSERT INTO bairros (bai_nu, ufe_sg, loc_nu, bai_no, bai_no_abrev) VALUES (?,?,?,?,?)",
        [
            (1, "SP", 1, "Sé", "Sé"),
            (2, "SP", 1, "Bela Vista", "B.Vista"),
            (3, "RJ", 2, "Centro", "Centro"),
        ],
    )
    conn.executemany(
        "INSERT INTO logradouros (log_nu, ufe_sg, loc_nu, bai_nu_ini, bai_nu_fim, log_no, log_complemento, cep, tlo_tx, log_sta_tlo, log_no_abrev) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (1, "SP", 1, 1, None, "Praça da Sé", None, "01001000", "Praça", "S", "Pg da Sé"),
            (2, "SP", 1, 2, None, "Paulista", None, "01310100", "Avenida", "S", "Av Paulista"),
            (3, "RJ", 2, 3, None, "Rio Branco", None, "20040002", "Avenida", "S", "Av Rio Branco"),
        ],
    )
    conn.commit()
    conn.close()
    return tmp_db


@pytest.fixture
def dne_sample_path():
    """Caminho para a amostra DNE de testes (variável de ambiente DNE_PATH)."""
    path = os.environ.get("DNE_PATH")
    if not path or not Path(path).is_dir():
        pytest.skip("DNE_PATH não configurado ou inválido — pulando teste de integração ETL.")
    return path
