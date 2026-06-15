"""Autenticação JWT + RBAC."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import jwt

from it_assets.config import settings
from it_assets.db import hash_password

ALGO = "HS256"


def authenticate(con: sqlite3.Connection, username: str, password: str) -> dict | None:
    row = con.execute(
        "SELECT username, password_hash, role FROM users WHERE username = ?", (username,)
    ).fetchone()
    if row is None:
        return None
    if row["password_hash"] != hash_password(password):
        return None
    return {"username": row["username"], "role": row["role"]}


def make_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
    except jwt.PyJWTError:
        return None
