"""Testes do módulo de consulta de CEP."""

import pytest

from cep_etl.query import CepNotFound, CepResult, normalize_cep, query_cep, query_ceps


class TestNormalizeCep:
    def test_cep_sem_mascara(self):
        assert normalize_cep("01001000") == "01001000"

    def test_cep_com_hifen(self):
        assert normalize_cep("01001-000") == "01001000"

    def test_cep_com_espacos(self):
        assert normalize_cep("  01001000  ") == "01001000"

    def test_cep_invalido_curto(self):
        with pytest.raises(ValueError, match="inválido"):
            normalize_cep("0100")

    def test_cep_invalido_longo(self):
        with pytest.raises(ValueError, match="inválido"):
            normalize_cep("010010001")

    def test_cep_invalido_letras(self):
        with pytest.raises(ValueError, match="inválido"):
            normalize_cep("ABCDEFGH")


class TestQueryCep:
    def test_encontra_logradouro_por_cep(self, loaded_db):
        result = query_cep("01001000", db_path=loaded_db)
        assert isinstance(result, CepResult)
        assert result.cep == "01001000"
        assert result.logradouro == "Praça da Sé"
        assert result.tipo_logradouro == "Praça"
        assert result.bairro == "Sé"
        assert result.localidade == "São Paulo"
        assert result.uf == "SP"
        assert result.fonte == "logradouro"

    def test_encontra_logradouro_com_hifen(self, loaded_db):
        result = query_cep("01001-000", db_path=loaded_db)
        assert isinstance(result, CepResult)
        assert result.cep == "01001000"

    def test_encontra_logradouro_rj(self, loaded_db):
        result = query_cep("20040002", db_path=loaded_db)
        assert isinstance(result, CepResult)
        assert result.logradouro == "Avenida Rio Branco"
        assert result.uf == "RJ"

    def test_fallback_localidade(self, loaded_db):
        """CEP de município (localidade) deve ser retornado como fallback."""
        result = query_cep("37564000", db_path=loaded_db)
        assert isinstance(result, CepResult)
        assert result.localidade == "Borda da Mata"
        assert result.uf == "MG"
        assert result.fonte == "localidade"
        assert result.logradouro is None
        assert result.bairro is None

    def test_cep_nao_encontrado(self, loaded_db):
        result = query_cep("99999999", db_path=loaded_db)
        assert isinstance(result, CepNotFound)
        assert "99999999" in result.erro

    def test_cep_invalido_retorna_not_found(self, loaded_db):
        result = query_cep("0000", db_path=loaded_db)
        assert isinstance(result, CepNotFound)
        assert "inválido" in result.erro


class TestQueryCeps:
    def test_consulta_multiplos(self, loaded_db):
        results = query_ceps(["01001000", "20040002"], db_path=loaded_db)
        assert len(results) == 2
        assert isinstance(results[0], CepResult)
        assert isinstance(results[1], CepResult)

    def test_lote_com_erro_nao_quebra(self, loaded_db):
        """Um CEP inválido no lote não deve interromper os demais."""
        results = query_ceps(["01001000", "INVALIDO", "20040002"], db_path=loaded_db)
        assert len(results) == 3
        assert isinstance(results[0], CepResult)
        assert isinstance(results[1], CepNotFound)
        assert isinstance(results[2], CepResult)

    def test_lote_com_nao_encontrado(self, loaded_db):
        results = query_ceps(["01001000", "99999999"], db_path=loaded_db)
        assert len(results) == 2
        assert isinstance(results[0], CepResult)
        assert isinstance(results[1], CepNotFound)
