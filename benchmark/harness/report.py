"""Gera results/leaderboard.md a partir dos results/<slug>/scores.json."""

from __future__ import annotations

import json
from pathlib import Path

from benchmark.harness.config import Config

# Descrição das colunas não-dimensionais.
META_COLUMNS = [
    ("#", "posição no ranking (ordenado pelo Subtotal)"),
    ("Harness", "o code agent que dirigiu o modelo (ex.: `claude_code`, `copilot_cli`)"),
    ("Modelo", "modelo avaliado; tag `· 1M` quando rodou em contexto de 1M"),
    ("Thinking", "esforço de raciocínio usado (Claude Code: `xhigh`, o default do harness; "
                 "Codex/Copilot GPT: `medium`)"),
    ("Subtotal", "soma ponderada das 9 dimensões (0–100, **antes** dos modificadores) — "
                 "critério de ordenação"),
    ("Score", "Subtotal + modificadores (bônus de performance, penalidades), com teto 100"),
    ("Tier", "faixa do Score: A (80+), B (60–79), C (40–59), D (<40)"),
    ("Tempo", "tempo total de conclusão (soma das 3 fases: build + validação + git)"),
    ("Custo (US$)", "custo-equivalente estimado das fases (referência; o consumo conta no plano)"),
    ("Diverg.", "dimensões com divergência grande entre os juízes (sinalizadas p/ revisão)"),
]


def _legend_lines(scenario) -> list[str]:
    lines = ["### Legenda das colunas", ""]
    for name, desc in META_COLUMNS[:8]:  # # .. Tempo
        lines.append(f"- **{name}** — {desc}")
    lines.append("")
    lines.append("Dimensões avaliadas (nota 0–100 por dimensão · peso na rubrica):")
    lines.append("")
    for dim in scenario.dimensions:
        lines.append(f"- **{scenario.dim_labels[dim]}** (peso {scenario.weights[dim]}) — "
                     f"{scenario.dim_descriptions[dim]}")
    lines.append("")
    for name, desc in META_COLUMNS[8:]:  # Custo, Diverg.
        lines.append(f"- **{name}** — {desc}")
    lines.append("")
    return lines


def _load_scores(cfg: Config, scenario) -> list[dict]:
    rows = []
    base = scenario.results_dir(cfg.results_dir)
    if not base.exists():
        return rows
    for scores_file in sorted(base.glob("*/scores.json")):
        try:
            row = json.loads(scores_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        slug = scores_file.parent.name
        run_logs = scenario.run_dir(cfg.runs_dir, slug) / "logs"
        row["_total_cost"] = _read_cost(scores_file.parent, run_logs)
        row["_total_duration"] = _read_duration(scores_file.parent, run_logs)
        rows.append(row)
    return rows


def _read_cost(results_slug_dir, run_logs_dir) -> float | None:
    """Custo total das fases. Prefere o result.json; cai para os logs das fases (que sobrevivem
    a re-avaliações com --skip-agent, que esvaziam as fases do result.json)."""
    costs = []
    result_file = results_slug_dir / "result.json"
    if result_file.exists():
        try:
            phases = json.loads(result_file.read_text(encoding="utf-8")).get("phases", {})
            costs = [p.get("cost_usd") for p in phases.values() if p.get("cost_usd")]
        except json.JSONDecodeError:
            costs = []
    if not costs:
        for pf in sorted(run_logs_dir.glob("phase*.json")) if run_logs_dir.exists() else []:
            try:
                c = json.loads(pf.read_text(encoding="utf-8")).get("cost_usd")
                if c:
                    costs.append(c)
            except json.JSONDecodeError:
                continue
    return round(sum(costs), 3) if costs else None


def _read_duration(results_slug_dir, run_logs_dir) -> float | None:
    """Tempo total (s) das fases (result.json; fallback nos logs locais)."""
    durs = []
    result_file = results_slug_dir / "result.json"
    if result_file.exists():
        try:
            phases = json.loads(result_file.read_text(encoding="utf-8")).get("phases", {})
            durs = [p.get("duration_s") for p in phases.values() if p.get("duration_s")]
        except json.JSONDecodeError:
            durs = []
    if not durs:
        for pf in sorted(run_logs_dir.glob("phase*.json")) if run_logs_dir.exists() else []:
            try:
                v = json.loads(pf.read_text(encoding="utf-8")).get("duration_s")
                if v:
                    durs.append(v)
            except json.JSONDecodeError:
                continue
    return round(sum(durs), 1) if durs else None


def _fmt_duration(seconds: float | None) -> str:
    """Formata segundos como 'Xm Ys' (ex.: 592.8 -> '9m 53s'); None -> '—'."""
    if not seconds:
        return "—"
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}m {s}s" if m else f"{s}s"


def build_leaderboard(cfg: Config, scenario=None) -> str:
    from benchmark.harness.scenarios.registry import get_scenario
    scenario = scenario or get_scenario("cep_etl")
    rows = _load_scores(cfg, scenario)
    # ordena por subtotal (pré-modificadores) — discrimina melhor que o final (satura no teto 100)
    def _key(r):
        sc = r.get("score", {})
        return (sc.get("weighted_subtotal", 0), sc.get("final_score", 0))

    rows.sort(key=_key, reverse=True)

    lines = [
        "# Leaderboard — Benchmark ETL CEP",
        "",
        "Ranking por **candidato = harness (agent) + modelo**. O mesmo modelo aparece como",
        "entradas distintas conforme o harness (o harness influencia o resultado).",
        "",
        "Ordenado por **Subtotal** (soma ponderada 0–100 pré-modificadores), que diferencia melhor",
        "que o Score final — este satura no teto 100 e inclui bônus/penalidades.",
        "",
    ]

    if not rows:
        lines.append("_Nenhum resultado ainda. Rode `uv run bench run` e depois "
                     "`uv run bench report`._")
        return "\n".join(lines) + "\n"

    lines += _legend_lines(scenario)

    header = "| # | Harness | Modelo | Thinking | Subtotal | Score | Tier | Tempo | " + \
        " | ".join(scenario.dim_labels[d] for d in scenario.dimensions) + \
        " | Custo (US$) | Diverg. |"
    sep = "|" + "---|" * (8 + len(scenario.dimensions) + 2)
    lines += [header, sep]

    for i, r in enumerate(rows, 1):
        sc = r.get("score", {})
        dims = sc.get("dimensions", {})
        dim_cells = " | ".join(
            str(int(round(dims.get(d, {}).get("note", 0)))) if dims.get(d) else "-"
            for d in scenario.dimensions
        )
        cost = f"{r['_total_cost']:.3f}" if r.get("_total_cost") else "—"
        tempo = _fmt_duration(r.get("_total_duration"))
        diverg = ", ".join(r.get("divergences", {}).keys()) or "—"
        # nome limpo de exibição; tag de contexto SÓ para modelos 1M
        cand = cfg.candidate_by_slug(r.get("slug", ""))
        model_label = (cand.display if cand and cand.display else r.get("model", "?"))
        if cand and cand.context and cand.context.upper() == "1M":
            model_label = f"{model_label} · 1M"
        thinking = (cand.thinking if cand and cand.thinking else "—")
        lines.append(
            f"| {i} | {r.get('agent','?')} | {model_label} | {thinking} | "
            f"**{sc.get('weighted_subtotal','?')}** | {sc.get('final_score','?')} | "
            f"{sc.get('tier','?')} | {tempo} | {dim_cells} | {cost} | {diverg} |"
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


def update_readme(cfg: Config, scenario) -> bool:
    """Injeta o leaderboard do cenário no README entre os marcadores próprios. True se atualizou."""
    from benchmark.harness.config import REPO_ROOT

    readme = REPO_ROOT / "README.md"
    if not readme.exists():
        return False
    start, end = scenario.markers
    text = readme.read_text(encoding="utf-8")
    if start not in text or end not in text:
        return False
    table = build_leaderboard(cfg, scenario)
    # remove o H1 "# Leaderboard ..." (a seção do README já encabeça)
    lines = table.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    table = "\n".join(lines)
    block = f"{start}\n\n{table}\n{end}"
    before = text.split(start)[0]
    after = text.split(end)[1]
    readme.write_text(before + block + after, encoding="utf-8")
    return True


def write_leaderboard(cfg: Config, scenario=None) -> Path:
    from benchmark.harness.scenarios.registry import get_scenario
    scenario = scenario or get_scenario("cep_etl")
    content = build_leaderboard(cfg, scenario)
    out = scenario.leaderboard_path(cfg.results_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    update_readme(cfg, scenario)
    return out
