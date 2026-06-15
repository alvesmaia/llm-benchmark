"""Helpers genéricos de checagens objetivas (caixa-preta via `uv run`), reutilizados pelos cenários.

Cada checagem retorna 0-100 e degrada graciosamente: nunca levanta exceção não tratada — falha vira
nota 0 com detalhe. As checagens específicas de cada cenário vivem em `benchmark/<id>/checks.py`.
"""

from __future__ import annotations

import re
import socket
from dataclasses import dataclass, field
from pathlib import Path

from benchmark.harness.adapters.base import run_command


@dataclass
class CheckResult:
    id: str
    dimension: str
    note: float
    detail: str = ""
    data: dict = field(default_factory=dict)


def _uv(args: list[str], cwd: Path, env: dict, timeout: int = 600):
    return run_command(["uv", "run", *args], cwd=cwd, env=env, timeout=timeout)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def check_pytest(app_dir: Path, env: dict) -> CheckResult:
    rc, out, err, _ = _uv(["pytest", "-q"], app_dir, env, timeout=900)
    blob = out + err
    m = re.search(r"(\d+) passed", blob)
    f = re.search(r"(\d+) failed", blob)
    passed = int(m.group(1)) if m else 0
    failed = int(f.group(1)) if f else 0
    if rc == 0:
        detail = f"{passed} passed" if m else "todos passaram (rc=0)"
        return CheckResult("pytest", "tests", 100.0, detail=detail)
    if rc == 5:
        return CheckResult("pytest", "tests", 0, detail="nenhum teste coletado")
    total = passed + failed
    note = (100 * passed / total) if total else 0
    return CheckResult("pytest", "tests", round(note, 1),
                       detail=f"{passed} passed / {failed} failed (rc={rc})")


def check_ruff(app_dir: Path, env: dict) -> CheckResult:
    rc, out, err, _ = _uv(["ruff", "check", "."], app_dir, env, timeout=300)
    if rc == 0:
        return CheckResult("ruff_ok", "production", 100, "sem erros de lint")
    blob = out + err
    n = len(re.findall(r"^\S+:\d+:\d+", blob, re.MULTILINE))
    note = 50 if n and n <= 10 else 20
    return CheckResult("ruff_ok", "production", note, detail=f"{n} achados de lint")


def check_ci_present(app_dir: Path) -> CheckResult:
    wf = app_dir / ".github" / "workflows"
    files = list(wf.glob("*.y*ml")) if wf.exists() else []
    if not files:
        return CheckResult("ci_present", "production", 0, "sem workflow de CI")
    txt = " ".join(p.read_text(encoding="utf-8", errors="replace") for p in files).lower()
    runs_tests = ("pytest" in txt or "test" in txt) and ("ruff" in txt or "lint" in txt)
    return CheckResult("ci_present", "production", 100 if runs_tests else 60,
                       detail="CI roda lint+testes" if runs_tests else "CI presente (parcial)")


def check_readme(app_dir: Path) -> CheckResult:
    for name in ("README.md", "readme.md", "README.rst"):
        p = app_dir / name
        if p.exists():
            txt = p.read_text(encoding="utf-8", errors="replace").lower()
            has_run = "uvx" in txt or "uv run" in txt or "run" in txt
            has_usage = "login" in txt or "uso" in txt or "usage" in txt or "serve" in txt \
                or "api" in txt
            note = 100 if (has_run and has_usage) else (60 if (has_run or has_usage) else 30)
            return CheckResult("readme_quality", "production", note,
                               detail=f"run={has_run}, uso={has_usage}")
    return CheckResult("readme_quality", "production", 0, "sem README")
