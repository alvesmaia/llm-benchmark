"""Testes da API REST FastAPI."""


import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(populated_db, monkeypatch):
    monkeypatch.setenv("DB_PATH", populated_db)
    # Reimportar para pegar o DB_PATH atualizado na query
    from cep_etl.api import app
    return TestClient(app)


class TestGetCep:
    def test_found(self, client):
        resp = client.get("/cep/01001000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cep"] == "01001000"
        assert data["found"] is True
        assert data["uf"] == "SP"

    def test_found_with_hyphen(self, client):
        resp = client.get("/cep/01001-000")
        assert resp.status_code == 200
        assert resp.json()["cep"] == "01001000"

    def test_not_found_returns_404(self, client):
        resp = client.get("/cep/00000000")
        assert resp.status_code == 404

    def test_invalid_cep_returns_404(self, client):
        resp = client.get("/cep/INVALID")
        assert resp.status_code == 404

    def test_fallback_localidade(self, client):
        resp = client.get("/cep/99999000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "localidade"


class TestPostCeps:
    def test_batch_found(self, client):
        resp = client.post("/ceps", json={"ceps": ["01001000", "01310100"]})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(d["found"] for d in data)

    def test_batch_mixed(self, client):
        resp = client.post("/ceps", json={"ceps": ["01001000", "00000000"]})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["found"] is True
        assert data[1]["found"] is False

    def test_batch_invalid_cep(self, client):
        resp = client.post("/ceps", json={"ceps": ["NOT_A_CEP"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["found"] is False

    def test_batch_empty(self, client):
        resp = client.post("/ceps", json={"ceps": []})
        assert resp.status_code == 200
        assert resp.json() == []


class TestWebInterface:
    def test_get_index(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "CEP" in resp.text

    def test_post_form_found(self, client):
        resp = client.post("/", data={"ceps": "01001000"})
        assert resp.status_code == 200
        assert "01001000" in resp.text
        assert "São Paulo" in resp.text

    def test_post_form_multiple(self, client):
        resp = client.post("/", data={"ceps": "01001000\n01310100"})
        assert resp.status_code == 200
        assert "01001000" in resp.text
        assert "01310100" in resp.text

    def test_post_form_not_found(self, client):
        resp = client.post("/", data={"ceps": "00000000"})
        assert resp.status_code == 200
        assert "não encontrado" in resp.text.lower()

    def test_post_form_empty(self, client):
        resp = client.post("/", data={"ceps": ""})
        assert resp.status_code == 200
        assert "pelo menos um CEP" in resp.text
