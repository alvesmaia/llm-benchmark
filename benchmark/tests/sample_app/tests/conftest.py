"""Fixtures de teste: gera uma base DNE mínima em Latin-1 e roda o ETL."""

from __future__ import annotations

import os

import pytest

from cep_etl.etl import load

LOCALIDADES = [
    ["1", "SP", "São Paulo", "", "0", "0", "", "S.Paulo", "3550308"],
    ["4", "MG", "Borda da Mata", "37564000", "1", "0", "", "Borda Mata", "3108503"],
]
BAIRROS = [["1", "SP", "1", "Sé", "Sé"]]
LOGRADOUROS_SP = [
    ["1", "SP", "1", "1", "", "Praça da Sé", "lado ímpar", "01001000", "Praça", "S", "Pç da Sé"],
]


def _write(path, rows):
    path.write_bytes(("\n".join("@".join(r) for r in rows) + "\n").encode("latin-1"))


@pytest.fixture()
def loaded_db(tmp_path, monkeypatch):
    dne = tmp_path / "dne"
    dne.mkdir()
    _write(dne / "LOG_LOCALIDADE.TXT", LOCALIDADES)
    _write(dne / "LOG_BAIRRO.TXT", BAIRROS)
    _write(dne / "LOG_LOGRADOURO_SP.TXT", LOGRADOUROS_SP)
    monkeypatch.setenv("DNE_PATH", str(dne))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "cep.db"))
    os.environ["DNE_PATH"] = str(dne)
    os.environ["DB_PATH"] = str(tmp_path / "cep.db")
    counts = load()
    return counts
