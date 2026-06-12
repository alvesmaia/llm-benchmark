"""Testes do ETL, consulta, fallback e tratamento de erros."""

from __future__ import annotations

import os

import pytest

from cep_etl.etl import DneError, load
from cep_etl.query import CepInvalidoError, lookup, lookup_many, normalize_cep


def test_load_counts(loaded_db):
    assert loaded_db["localidade"] == 2
    assert loaded_db["logradouro"] == 1


def test_lookup_logradouro(loaded_db):
    r = lookup("01001000")
    assert r is not None
    assert r["logradouro"] == "Praça da Sé"
    assert r["bairro"] == "Sé"
    assert r["localidade"] == "São Paulo"
    assert r["uf"] == "SP"


def test_lookup_aceita_mascara(loaded_db):
    assert lookup("01001-000")["logradouro"] == "Praça da Sé"


def test_fallback_localidade(loaded_db):
    r = lookup("37564000")
    assert r is not None
    assert r["localidade"] == "Borda da Mata"
    assert r["uf"] == "MG"
    assert "logradouro" not in r


def test_not_found(loaded_db):
    assert lookup("99999999") is None


def test_cep_invalido():
    with pytest.raises(CepInvalidoError):
        normalize_cep("abc")
    with pytest.raises(CepInvalidoError):
        normalize_cep("123")


def test_lookup_many_nao_quebra(loaded_db):
    out = lookup_many(["01001000", "abc", "99999999"])
    assert len(out) == 3
    assert out[0]["logradouro"] == "Praça da Sé"
    assert "inválido" in out[1]["erro"].lower()
    assert out[2]["erro"] == "não encontrado"


def test_idempotente(loaded_db, tmp_path):
    # roda o load de novo; contagem por PK não deve mudar
    from cep_etl.db import connect

    con = connect()
    before = con.execute("SELECT COUNT(*) FROM logradouro").fetchone()[0]
    con.close()
    load()
    con = connect()
    after = con.execute("SELECT COUNT(*) FROM logradouro").fetchone()[0]
    con.close()
    assert before == after


def test_dne_ausente(tmp_path, monkeypatch):
    monkeypatch.setenv("DNE_PATH", str(tmp_path / "vazio"))
    os.environ["DNE_PATH"] = str(tmp_path / "vazio")
    with pytest.raises(DneError):
        load()
