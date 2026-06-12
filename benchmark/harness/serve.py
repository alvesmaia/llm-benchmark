"""Runner local: sobe (ou consulta) o projeto gerado por um candidato em um único comando.

`uv run bench serve <slug>` carrega o DNE/fixture e sobe Web+API do projeto escolhido.
Internamente delega ao console script `cep-etl` do projeto gerado (via `uv run` no diretório dele).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from benchmark.harness.config import Config


def _app_dir(cfg: Config, slug: str) -> Path:
    app_dir = cfg.runs_dir / slug / "app"
    if not app_dir.exists():
        raise FileNotFoundError(
            f"projeto gerado não encontrado: {app_dir}\n"
            f"Rode `uv run bench run --only {slug}` primeiro."
        )
    return app_dir


def _env(cfg: Config, app_dir: Path) -> dict:
    env = dict(os.environ)
    env["DNE_PATH"] = str(cfg.dne_path)
    env["DB_PATH"] = str(app_dir / "cep.db")
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def serve(cfg: Config, slug: str, *, host: str = "127.0.0.1", port: int = 8000,
          load_first: bool = True) -> int:
    app_dir = _app_dir(cfg, slug)
    env = _env(cfg, app_dir)
    if load_first:
        print(f"[bench] carregando DNE ({cfg.dne_path}) em {env['DB_PATH']} ...")
        subprocess.run(["uv", "run", "cep-etl", "load"], cwd=str(app_dir), env=env, check=False)
    print(f"[bench] subindo {slug} em http://{host}:{port} (Ctrl+C para parar)")
    return subprocess.run(
        ["uv", "run", "cep-etl", "serve", "--host", host, "--port", str(port)],
        cwd=str(app_dir), env=env, check=False,
    ).returncode


def query(cfg: Config, slug: str, ceps: list[str], *, as_json: bool = False) -> int:
    app_dir = _app_dir(cfg, slug)
    env = _env(cfg, app_dir)
    args = ["uv", "run", "cep-etl", "query", *ceps]
    if as_json:
        args.append("--json")
    return subprocess.run(args, cwd=str(app_dir), env=env, check=False).returncode
