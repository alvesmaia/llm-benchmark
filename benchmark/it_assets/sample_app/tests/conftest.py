"""Fixtures de teste: banco temporário carregado a partir do CSV em data/."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture()
def loaded_con(db_path):
    os.environ["DB_PATH"] = db_path
    from it_assets.db import connect, init_db, seed_users
    from it_assets.ingest import load_csv

    con = connect(db_path)
    init_db(con)
    seed_users(con)
    load_csv(con, str(ROOT / "data" / "movements.csv"))
    yield con
    con.close()


@pytest.fixture()
def client(db_path):
    os.environ["DB_PATH"] = db_path
    from fastapi.testclient import TestClient

    from it_assets.web import create_app

    with TestClient(create_app()) as c:
        yield c
