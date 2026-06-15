"""Configuração: carrega o .env versionado automaticamente e expõe as settings."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# raiz do projeto (dois níveis acima: it_assets/config.py -> <root>)
ROOT = Path(__file__).resolve().parents[1]

# carrega o .env versionado (com valores) — automático, sem precisar exportar nada
load_dotenv(ROOT / ".env")


def _default_dataset() -> str:
    """DATASET_PATH tem prioridade; senão usa o CSV copiado em data/."""
    env = os.environ.get("DATASET_PATH")
    if env:
        return env
    data_dir = ROOT / "data"
    if data_dir.exists():
        csvs = sorted(data_dir.glob("*.csv"))
        if csvs:
            return str(csvs[0])
    return str(ROOT / "data" / "movements.csv")


class Settings:
    jwt_secret: str = os.environ.get("JWT_SECRET", "demo-secret-it-assets-change-me")
    admin_user: str = os.environ.get("ADMIN_USER", "admin")
    admin_password: str = os.environ.get("ADMIN_PASSWORD", "admin123")
    viewer_user: str = os.environ.get("VIEWER_USER", "viewer")
    viewer_password: str = os.environ.get("VIEWER_PASSWORD", "viewer123")

    @property
    def db_path(self) -> str:
        return os.environ.get("DB_PATH", str(ROOT / "it_assets.db"))

    @property
    def dataset_path(self) -> str:
        return _default_dataset()


settings = Settings()
