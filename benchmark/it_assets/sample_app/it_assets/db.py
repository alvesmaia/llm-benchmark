"""Persistência SQLite: schema, conexão e seed de usuários (com senha em hash)."""

from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

from it_assets.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer'
);
CREATE TABLE IF NOT EXISTS movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movement_id TEXT,
    date TEXT,
    asset_tag TEXT NOT NULL,
    asset_type TEXT,
    action TEXT NOT NULL,
    employee TEXT,
    from_location TEXT,
    to_location TEXT,
    status TEXT,
    value REAL
);
CREATE INDEX IF NOT EXISTS idx_movements_asset_tag ON movements(asset_tag);
CREATE INDEX IF NOT EXISTS idx_movements_action ON movements(action);
"""


def hash_password(password: str, *, salt: str = "it-assets") -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    ).hex()


def connect(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or settings.db_path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def seed_users(con: sqlite3.Connection) -> None:
    """Semeia admin (escrita) e viewer (somente leitura) a partir das settings/.env."""
    users = [
        (settings.admin_user, settings.admin_password, "admin"),
        (settings.viewer_user, settings.viewer_password, "viewer"),
    ]
    for username, password, role in users:
        existing = con.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing is None:
            con.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, hash_password(password), role),
            )
    con.commit()


def reset_db(db_path: str | None = None) -> None:
    """Remove o banco (útil para recarga limpa)."""
    path = db_path or settings.db_path
    if os.path.exists(path):
        os.remove(path)
