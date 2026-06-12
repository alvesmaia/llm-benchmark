"""Testes da API REST FastAPI."""


import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(loaded_db, monkeypatch):
    monkeypatch.setenv("DB_PATH", loaded_db)
    from cep_etl.api import app
    return TestClient(app)


class TestGetCep:
    def test_cep_encontrado(self, client):
        resp = client.get("/cep/01001000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cep"] == "01001000"
        assert data["localidade"] == "São Paulo"
        assert data["uf"] == "SP"
        assert data["encontrado"] is True

    def test_cep_com_hifen(self, client):
        resp = client.get("/cep/01001-000")
        assert resp.status_code == 200
        assert resp.json()["cep"] == "01001000"

    def test_cep_nao_encontrado_retorna_404(self, client):
        resp = client.get("/cep/99999999")
        assert resp.status_code == 404

    def test_cep_invalido_retorna_404(self, client):
        resp = client.get("/cep/0000")
        assert resp.status_code == 404

    def test_cep_localidade_fallback(self, client):
        resp = client.get("/cep/37564000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["localidade"] == "Borda da Mata"
        assert data["fonte"] == "localidade"


class TestPostCeps:
    def test_lote_encontrado(self, client):
        resp = client.post("/ceps", json={"ceps": ["01001000", "20040002"]})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["encontrado"] is True
        assert data[1]["encontrado"] is True

    def test_lote_com_nao_encontrado(self, client):
        resp = client.post("/ceps", json={"ceps": ["01001000", "99999999"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["encontrado"] is True
        assert data[1]["encontrado"] is False

    def test_lote_vazio_retorna_422(self, client):
        resp = client.post("/ceps", json={"ceps": []})
        assert resp.status_code == 422


class TestWebInterface:
    def test_pagina_inicial(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "CEP" in resp.text
        assert "<form" in resp.text

    def test_formulario_consulta(self, client):
        resp = client.post("/", data={"ceps": "01001000"})
        assert resp.status_code == 200
        assert "Praça da Sé" in resp.text or "01001000" in resp.text

    def test_formulario_multiplos_ceps(self, client):
        resp = client.post("/", data={"ceps": "01001000\n20040002"})
        assert resp.status_code == 200
        assert "01001" in resp.text

    def test_formulario_vazio(self, client):
        resp = client.post("/", data={"ceps": ""})
        assert resp.status_code == 200
        assert "pelo menos um CEP" in resp.text
