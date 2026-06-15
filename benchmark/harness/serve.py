"""Runner local: sobe o projeto gerado por um candidato em um único comando.

`uv run bench serve <slug>` sobe a app (FastAPI/Web) do projeto escolhido, delegando ao console
script `it-assets` do projeto gerado (via `uv run` no diretório dele), com o `.env`/base do cenário.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from benchmark.harness.config import Config
from benchmark.harness.scenarios.registry import get_scenario


def _app_dir(cfg: Config, slug: str, scenario) -> Path:
    app_dir = scenario.run_dir(cfg.runs_dir, slug) / "app"
    if not app_dir.exists():
        raise FileNotFoundError(
            f"projeto gerado não encontrado: {app_dir}\n"
            f"Rode `uv run bench run --only {slug}` primeiro."
        )
    return app_dir


def _console_script(app_dir: Path) -> str:
    pp = app_dir / "pyproject.toml"
    if pp.exists():
        txt = pp.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^\s*([\w-]+)\s*=\s*[\"'][\w_]+(?:\.[\w_]+)*:", txt, re.MULTILINE)
        if m:
            return m.group(1)
    return "it-assets"


def _env(cfg: Config, app_dir: Path, scenario) -> dict:
    env = dict(os.environ)
    env[scenario.dataset_env] = str(cfg.dataset_for(scenario.id))
    env["DB_PATH"] = str(app_dir / scenario.db_filename)
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(scenario.extra_env)
    return env


def serve(cfg: Config, slug: str, *, host: str = "127.0.0.1", port: int = 8000,
          scenario=None) -> int:
    scenario = scenario or get_scenario()
    app_dir = _app_dir(cfg, slug, scenario)
    env = _env(cfg, app_dir, scenario)
    script = _console_script(app_dir)
    print(f"[bench] subindo {slug} em http://{host}:{port} (Ctrl+C para parar)")
    return subprocess.run(
        ["uv", "run", script, "serve", "--host", host, "--port", str(port)],
        cwd=str(app_dir), env=env, check=False,
    ).returncode
