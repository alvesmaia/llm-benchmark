"""Testes de import, auth (hash/login), estoque (in/out) e dashboard."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from inv_etl import auth, inventory
from inv_etl.api import app
from inv_etl.db import connect, init_schema
from inv_etl.etl import DatasetError, import_sales


# ---------------------------------------------------------------------------
# ETL / import
# ---------------------------------------------------------------------------
def test_import_counts(env_db):
    counts = import_sales()
    assert counts["products"] == 2  # Ford/Fiesta, Toyota/Corolla
    assert counts["movements"] == 3


def test_import_idempotente(env_db):
    import_sales()
    con = connect()
    before = con.execute("SELECT COUNT(*) FROM movements").fetchone()[0]
    con.close()
    import_sales()
    con = connect()
    after = con.execute("SELECT COUNT(*) FROM movements").fetchone()[0]
    con.close()
    assert before == after == 3


def test_import_dataset_ausente(tmp_path, monkeypatch):
    monkeypatch.setenv("DATASET_PATH", str(tmp_path / "nao_existe.csv"))
    with pytest.raises(DatasetError):
        import_sales()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def test_password_hashed(env_db):
    con = connect()
    init_schema(con)
    auth.seed_admin(con)
    row = con.execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()
    con.close()
    assert row is not None
    assert row["password_hash"] != "admin123"  # nunca texto plano
    assert row["password_hash"].startswith("pbkdf2_")


def test_login_valido_invalido(env_db):
    con = connect()
    init_schema(con)
    auth.seed_admin(con)
    assert auth.login(con, "admin", "admin123") is not None
    assert auth.login(con, "admin", "errado") is None
    con.close()


# ---------------------------------------------------------------------------
# Estoque (in/out)
# ---------------------------------------------------------------------------
def test_stock_in_out(env_db):
    con = connect()
    init_schema(con)
    pid = inventory.upsert_product(con, "Ford", "Ka", unit_cost=100)
    inventory.register_movement(con, pid, "in", 10)
    assert inventory.get_product(con, pid)["stock"] == 10
    inventory.register_movement(con, pid, "out", 3)
    assert inventory.get_product(con, pid)["stock"] == 7
    with pytest.raises(inventory.StockError):
        inventory.register_movement(con, pid, "out", 100)
    con.close()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def test_dashboard_metrics(env_db):
    import_sales()
    con = connect()
    dash = inventory.dashboard(con)
    con.close()
    assert dash["units_sold"] == 3
    assert dash["revenue"] == 26000 + 19000 + 42000
    assert dash["by_company"]["Ford"] == 26000 + 19000
    assert dash["by_region"]["Curitiba"] == 42000


# ---------------------------------------------------------------------------
# API (auth obrigatório + fluxo)
# ---------------------------------------------------------------------------
def test_api_auth_required(env_db):
    client = TestClient(app)
    r = client.post("/api/products", json={"company": "X", "model": "Y", "unit_cost": 1})
    assert r.status_code in (401, 403)


def test_api_login_and_crud(env_db):
    client = TestClient(app)
    r = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/api/products",
                    json={"company": "Honda", "model": "City", "unit_cost": 50}, headers=headers)
    assert r.status_code == 201
    pid = r.json()["id"]

    r = client.get("/api/products")
    assert any(p["id"] == pid for p in r.json())

    r = client.post("/api/movements",
                    json={"product_id": pid, "type": "in", "qty": 5}, headers=headers)
    assert r.status_code == 201
    r = client.post("/api/movements",
                    json={"product_id": pid, "type": "out", "qty": 99}, headers=headers)
    assert r.status_code == 400  # estoque insuficiente


def test_web_form(env_db):
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert "<form" in r.text.lower()
