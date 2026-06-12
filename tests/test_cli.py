"""Testes da interface CLI."""

import json

import pytest
from click.testing import CliRunner

from cep_etl.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestLoadCommand:
    def test_load_sucesso(self, runner, dne_path, db_path):
        result = runner.invoke(main, ["load", "--db-path", db_path, "--dne-path", dne_path])
        assert result.exit_code == 0
        assert "ETL concluído" in result.output
        assert "localidades" in result.output

    def test_load_sem_dne_path(self, runner, db_path, monkeypatch):
        monkeypatch.delenv("DNE_PATH", raising=False)
        result = runner.invoke(main, ["load", "--db-path", db_path])
        assert result.exit_code != 0
        assert "Erro" in result.output or "DNE_PATH" in result.output


class TestQueryCommand:
    def test_query_um_cep(self, runner, loaded_db):
        result = runner.invoke(main, ["query", "--db-path", loaded_db, "01001000"])
        assert result.exit_code == 0
        assert "01001000" in result.output
        assert "São Paulo" in result.output or "SP" in result.output

    def test_query_multiplos_ceps(self, runner, loaded_db):
        result = runner.invoke(main, ["query", "--db-path", loaded_db, "01001000", "20040002"])
        assert result.exit_code == 0
        assert "01001000" in result.output
        assert "20040002" in result.output

    def test_query_json(self, runner, loaded_db):
        result = runner.invoke(main, ["query", "--db-path", loaded_db, "--json", "01001000"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["cep"] == "01001000"
        assert data[0]["encontrado"] is True

    def test_query_cep_nao_encontrado(self, runner, loaded_db):
        result = runner.invoke(main, ["query", "--db-path", loaded_db, "99999999"])
        assert result.exit_code != 0
        assert "NÃO ENCONTRADO" in result.output or "não encontrado" in result.output.lower()

    def test_query_cep_com_hifen(self, runner, loaded_db):
        result = runner.invoke(main, ["query", "--db-path", loaded_db, "01001-000"])
        assert result.exit_code == 0
        assert "01001000" in result.output or "São Paulo" in result.output
