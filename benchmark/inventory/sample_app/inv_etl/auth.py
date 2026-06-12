"""Autenticação: hash de senha (pbkdf2), seed do admin, login e tokens Bearer."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3

_ITERATIONS = 120_000
_ALGO = "sha256"

# Tokens em memória (suficiente para o escopo do desafio). token -> username.
_TOKENS: dict[str, str] = {}


def hash_password(password: str, *, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(_ALGO, password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return f"pbkdf2_{_ALGO}${_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _scheme, iterations, salt, digest = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            _ALGO, password.encode("utf-8"), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(dk.hex(), digest)
    except (ValueError, AttributeError):
        return False


def seed_admin(con: sqlite3.Connection) -> None:
    """Cria o usuário admin a partir de ADMIN_USER/ADMIN_PASSWORD (senha em HASH)."""
    user = os.environ.get("ADMIN_USER", "admin")
    pwd = os.environ.get("ADMIN_PASSWORD", "admin123")
    row = con.execute("SELECT id FROM users WHERE username = ?", (user,)).fetchone()
    if row is None:
        con.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (user, hash_password(pwd)),
        )
        con.commit()


def login(con: sqlite3.Connection, username: str, password: str) -> str | None:
    row = con.execute(
        "SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        return None
    token = secrets.token_urlsafe(24)
    _TOKENS[token] = username
    return token


def user_for_token(token: str | None) -> str | None:
    if not token:
        return None
    return _TOKENS.get(token)
