"""Testes: ingestão/persistência, JWT, RBAC, métricas e robustez a dados sujos."""

from __future__ import annotations

import csv

from it_assets.config import settings
from it_assets.ingest import _norm_action, _parse_date, _parse_value, load_csv
from it_assets.metrics import dashboard_metrics, list_assets


def test_ingest_populates(loaded_con):
    n = loaded_con.execute("SELECT COUNT(*) AS n FROM movements").fetchone()["n"]
    assert n >= 20


def test_idempotent_load(loaded_con):
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    before = loaded_con.execute("SELECT COUNT(*) AS n FROM movements").fetchone()["n"]
    load_csv(loaded_con, str(root / "data" / "movements.csv"))
    after = loaded_con.execute("SELECT COUNT(*) AS n FROM movements").fetchone()["n"]
    assert before == after


def test_metrics(loaded_con):
    m = dashboard_metrics(loaded_con)
    assert m["total_movements"] >= 20
    assert m["distinct_assets"] >= 1
    assert "allocate" in m["by_action"]
    assert list_assets(loaded_con)


def test_login_valid_and_invalid(client):
    ok = client.post(
        "/auth/login",
        json={"username": settings.admin_user, "password": settings.admin_password},
    )
    assert ok.status_code == 200
    assert ok.json().get("token")

    bad = client.post(
        "/auth/login", json={"username": settings.admin_user, "password": "errada"}
    )
    assert bad.status_code == 401


def test_protected_requires_token(client):
    r = client.post("/api/movements", json={"asset_tag": "X-1", "action": "allocate"})
    assert r.status_code == 401


def test_rbac_viewer_denied(client):
    login = client.post(
        "/auth/login",
        json={"username": settings.viewer_user, "password": settings.viewer_password},
    )
    token = login.json()["token"]
    r = client.post(
        "/api/movements",
        json={"asset_tag": "X-1", "action": "allocate"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_admin_can_write(client):
    login = client.post(
        "/auth/login",
        json={"username": settings.admin_user, "password": settings.admin_password},
    )
    token = login.json()["token"]
    r = client.post(
        "/api/movements",
        json={"asset_tag": "X-1", "action": "allocate"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201


def test_web_login_form(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.text.lower()
    assert "<form" in body and "username" in body and "password" in body


def test_parse_helpers_robust():
    # valor negativo é saneado para 0; vazio -> None; lixo -> None
    assert _parse_value("-50") == 0.0
    assert _parse_value("") is None
    assert _parse_value("abc") is None
    assert _parse_value("1200.50") == 1200.50
    # datas em formatos alternativos
    assert _parse_date("2024-03-15") == "2024-03-15"
    assert _parse_date("15/03/2024") == "2024-03-15"
    assert _parse_date("") is None
    # ação fora do domínio vira 'other'
    assert _norm_action("decommission_xyz") == "other"
    assert _norm_action("allocate") == "allocate"


def test_load_survives_dirty_data(tmp_path, loaded_con):
    """Simula a perturbação da Fase 3: nulos, ação inválida, valor negativo, data alt, id dup."""
    dirty = tmp_path / "dirty.csv"
    header = [
        "movement_id", "date", "asset_tag", "asset_type", "action",
        "employee", "from_location", "to_location", "status", "value",
    ]
    rows = [
        ["MV-1", "2024-01-01", "NB-1", "notebook", "allocate", "", "A", "B", "in_use", ""],
        ["MV-1", "01/02/2024", "NB-2", "notebook", "decommission_xyz", "x",
         "A", "B", "in_use", "-99"],
    ]
    with dirty.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    n = load_csv(loaded_con, str(dirty))
    assert n == 2  # nenhuma linha derrubou a carga
    m = dashboard_metrics(loaded_con)
    assert m["total_movements"] == 2
