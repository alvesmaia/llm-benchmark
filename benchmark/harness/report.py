"""Gera results/leaderboard.md a partir dos results/<slug>/scores.json."""

from __future__ import annotations

import json
from pathlib import Path

from benchmark.harness.config import Config
from benchmark.harness.rubric import DIMENSIONS

DIM_LABELS = {
    "etl_parsing": "ETL",
    "completeness": "Compl.",
    "interfaces": "Interf.",
    "persistence": "Persist.",
    "tests": "Testes",
    "error_handling": "Erros",
    "architecture": "Arquit.",
    "production": "Prod.",
    "git": "Git",
}


def _load_scores(cfg: Config) -> list[dict]:
    rows = []
    if not cfg.results_dir.exists():
        return rows
    for scores_file in sorted(cfg.results_dir.glob("*/scores.json")):
        try:
            row = json.loads(scores_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        # custo total das fases vem do result.json irmão (quando o agente expõe)
        result_file = scores_file.parent / "result.json"
        if result_file.exists():
            try:
                phases = json.loads(result_file.read_text(encoding="utf-8")).get("phases", {})
                costs = [p.get("cost_usd") for p in phases.values() if p.get("cost_usd")]
                row["_total_cost"] = round(sum(costs), 3) if costs else None
            except json.JSONDecodeError:
                row["_total_cost"] = None
        rows.append(row)
    return rows


def build_leaderboard(cfg: Config) -> str:
    rows = _load_scores(cfg)
    rows.sort(key=lambda r: r.get("score", {}).get("final_score", 0), reverse=True)

    lines = [
        "# Leaderboard — Benchmark ETL CEP",
        "",
        "Ranking por **candidato = harness (agent) + modelo**. O mesmo modelo aparece como",
        "entradas distintas conforme o harness (o harness influencia o resultado).",
        "",
    ]

    if not rows:
        lines.append("_Nenhum resultado ainda. Rode `uv run bench run` e depois "
                     "`uv run bench report`._")
        return "\n".join(lines) + "\n"

    header = "| # | Harness | Modelo | Score | Tier | " + \
        " | ".join(DIM_LABELS[d] for d in DIMENSIONS) + " | Custo (US$) | Diverg. |"
    sep = "|" + "---|" * (5 + len(DIMENSIONS) + 2)
    lines += [header, sep]

    for i, r in enumerate(rows, 1):
        sc = r.get("score", {})
        dims = sc.get("dimensions", {})
        dim_cells = " | ".join(
            str(int(round(dims.get(d, {}).get("note", 0)))) if dims.get(d) else "-"
            for d in DIMENSIONS
        )
        cost = f"{r['_total_cost']:.3f}" if r.get("_total_cost") else "—"
        diverg = ", ".join(r.get("divergences", {}).keys()) or "—"
        lines.append(
            f"| {i} | {r.get('agent','?')} | {r.get('model','?')} | "
            f"**{sc.get('final_score','?')}** | {sc.get('tier','?')} | {dim_cells} | "
            f"{cost} | {diverg} |"
        )

    lines += [
        "",
        "## Modificadores aplicados",
        "",
    ]
    for r in rows:
        mods = r.get("score", {}).get("modifiers_applied", [])
        if mods:
            desc = ", ".join(f"{m['id']} ({m['value']:+d})" for m in mods)
            lines.append(f"- **{r.get('agent')}-{r.get('model')}**: {desc}")
    if not any(r.get("score", {}).get("modifiers_applied") for r in rows):
        lines.append("- (nenhum)")

    return "\n".join(lines) + "\n"


def write_leaderboard(cfg: Config) -> Path:
    content = build_leaderboard(cfg)
    out = cfg.results_dir / "leaderboard.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return out
