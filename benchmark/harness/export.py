"""Exporta, por candidato, um ZIP com o projeto gerado + o prompt do juiz + os resultados.

Objetivo: permitir reavaliação por um juiz EXTERNO — reaproveitar o mesmo `judge_prompt.md`
(idêntico ao usado pelo painel interno) e enviar o ZIP (app completo) a outro modelo.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from benchmark.harness.config import REPO_ROOT, Config

_SKIP_DIRS = {".venv", "__pycache__", ".git", ".ruff_cache", ".pytest_cache", "node_modules",
             "htmlcov"}


def _add_tree(zf: zipfile.ZipFile, root: Path, arc_prefix: str) -> int:
    n = 0
    if not root.exists():
        return n
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        if p.is_file():
            zf.write(p, f"{arc_prefix}/{rel.as_posix()}")
            n += 1
    return n


def export_candidate(cfg: Config, slug: str, scenario, out_dir: Path | None = None) -> Path:
    """Empacota app/ + logs/ (inclui judge_prompt.md) + scores/result.json num ZIP. Retorna o
    caminho. Default de saída: exports/[<scenario>/]<slug>.zip (diretório gitignored)."""
    run_dir = scenario.run_dir(cfg.runs_dir, slug)
    app_dir = run_dir / "app"
    logs_dir = run_dir / "logs"
    res_dir = scenario.results_dir(cfg.results_dir) / slug

    out_base = out_dir or (REPO_ROOT / "exports" / (scenario.results_subdir or scenario.id))
    out_base.mkdir(parents=True, exist_ok=True)
    out = out_base / f"{slug}.zip"

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        _add_tree(zf, app_dir, "app")
        _add_tree(zf, logs_dir, "logs")
        for name in ("scores.json", "result.json"):
            f = res_dir / name
            if f.exists():
                zf.write(f, f"results/{name}")
        # também na raiz do ZIP, p/ acesso direto pelo juiz externo
        jp = logs_dir / "judge_prompt.md"
        if jp.exists():
            zf.write(jp, "judge_prompt.md")
    return out


def export_all(cfg: Config, scenario, slugs: list[str] | None = None) -> list[Path]:
    base = scenario.results_dir(cfg.results_dir)
    if slugs is None:
        slugs = [d.name for d in base.glob("*") if (d / "scores.json").exists()] \
            if base.exists() else []
    return [export_candidate(cfg, s, scenario) for s in slugs]
