"""Testes do módulo de consulta de CEPs."""

import pytest

from cep_etl.query import (
    CepNotFound,
    CepResult,
    normalize_cep,
    query_cep,
    query_ceps,
    result_to_dict,
)

# ---------------------------------------------------------------------------
# normalize_cep
# ---------------------------------------------------------------------------

class TestNormalizeCep:
    def test_already_normalized(self):
        assert normalize_cep("01001000") == "01001000"

    def test_with_hyphen(self):
        assert normalize_cep("01001-000") == "01001000"

    def test_with_spaces(self):
        assert normalize_cep("  01001000  ") == "01001000"

    def test_with_dot(self):
        assert normalize_cep("01001.000") == "01001000"

    def test_too_short(self):
        with pytest.raises(ValueError, match="inválido"):
            normalize_cep("1234567")

    def test_too_long(self):
        with pytest.raises(ValueError, match="inválido"):
            normalize_cep("123456789")

    def test_non_numeric(self):
        with pytest.raises(ValueError, match="inválido"):
            normalize_cep("0100100A")

    def test_empty(self):
        with pytest.raises(ValueError, match="inválido"):
            normalize_cep("")


# ---------------------------------------------------------------------------
# query_cep — usando populated_db
# ---------------------------------------------------------------------------

class TestQueryCep:
    def test_found_logradouro(self, populated_db):
        result = query_cep("01001000", db_path=populated_db)
        assert isinstance(result, CepResult)
        assert result.cep == "01001000"
        assert result.logradouro == "Praça da Sé"
        assert result.tipo_logradouro == "Praça"
        assert result.bairro == "Sé"
        assert result.localidade == "São Paulo"
        assert result.uf == "SP"
        assert result.source == "logradouro"

    def test_found_with_hyphen(self, populated_db):
        result = query_cep("01001-000", db_path=populated_db)
        assert isinstance(result, CepResult)
        assert result.cep == "01001000"

    def test_found_rj(self, populated_db):
        result = query_cep("20040002", db_path=populated_db)
        assert isinstance(result, CepResult)
        assert result.uf == "RJ"
        assert result.localidade == "Rio de Janeiro"

    def test_not_found(self, populated_db):
        result = query_cep("00000000", db_path=populated_db)
        assert isinstance(result, CepNotFound)
        assert result.found is False
        assert "não encontrado" in result.error.lower()

    def test_invalid_format(self, populated_db):
        result = query_cep("invalid", db_path=populated_db)
        assert isinstance(result, CepNotFound)
        assert result.found is False

    def test_fallback_localidade(self, populated_db):
        """CEP de localidade (não logradouro) deve ser retornado via fallback."""
        result = query_cep("99999000", db_path=populated_db)
        assert isinstance(result, CepResult)
        assert result.localidade == "Município Teste"
        assert result.source == "localidade"
        assert result.logradouro is None


class TestQueryCeps:
    def test_multiple_ceps(self, populated_db):
        results = query_ceps(["01001000", "20040002"], db_path=populated_db)
        assert len(results) == 2
        assert all(isinstance(r, CepResult) for r in results)

    def test_mixed_found_not_found(self, populated_db):
        results = query_ceps(["01001000", "00000000"], db_path=populated_db)
        assert len(results) == 2
        assert isinstance(results[0], CepResult)
        assert isinstance(results[1], CepNotFound)

    def test_invalid_in_batch_does_not_break_others(self, populated_db):
        results = query_ceps(["INVALID", "01001000"], db_path=populated_db)
        assert len(results) == 2
        assert isinstance(results[0], CepNotFound)
        assert isinstance(results[1], CepResult)

    def test_empty_list(self, populated_db):
        results = query_ceps([], db_path=populated_db)
        assert results == []


class TestResultToDict:
    def test_found_result(self, populated_db):
        result = query_cep("01001000", db_path=populated_db)
        d = result_to_dict(result)
        assert d["found"] is True
        assert d["cep"] == "01001000"
        assert "logradouro" in d
        assert "bairro" in d
        assert "localidade" in d
        assert "uf" in d

    def test_not_found_result(self, populated_db):
        result = query_cep("00000000", db_path=populated_db)
        d = result_to_dict(result)
        assert d["found"] is False
        assert "error" in d


# ---------------------------------------------------------------------------
# Integração com base real
# ---------------------------------------------------------------------------

class TestQueryIntegration:
    def test_query_real_cep_sp(self, dne_sample_path, tmp_path):
        """Consulta um CEP real da amostra SP após ETL."""
        from cep_etl.etl import run_etl
        db_path = str(tmp_path / "cep.db")
        run_etl(dne_path=dne_sample_path, db_path=db_path)

        result = query_cep("01001000", db_path=db_path)
        assert isinstance(result, CepResult)
        assert result.uf == "SP"

    def test_query_real_cep_rj(self, dne_sample_path, tmp_path):
        """Consulta um CEP real da amostra RJ após ETL."""
        from cep_etl.etl import run_etl
        db_path = str(tmp_path / "cep.db")
        run_etl(dne_path=dne_sample_path, db_path=db_path)

        # CEP do Rio de Janeiro na amostra
        result = query_cep("20040002", db_path=db_path)
        assert isinstance(result, CepResult)
        assert result.uf == "RJ"
