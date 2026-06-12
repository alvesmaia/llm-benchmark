"""Gera results/leaderboard.md a partir dos results/<slug>/scores.json."""

from __future__ import annotations

import json
from pathlib import Path

from benchmark.harness.config import Config
from benchmark.harness.rubric import DIMENSIONS, WEIGHTS

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

# Descrição de cada dimensão no contexto do desafio (ETL CEP Correios).
DIM_DESCRIPTIONS = {
    "etl_parsing": "correção do ETL/parsing da base DNE (encoding Latin-1, separador `@`, "
                   "mapeamento de campos, fallback de CEP de localidade)",
    "completeness": "completude dos entregáveis obrigatórios (ETL, consulta, CLI, API, Web, "
                    "testes, README, lint/CI)",
    "interfaces": "as três interfaces de consulta (CLI, API REST e Web) funcionam, aceitam 1+ "
                  "CEPs, e o projeto roda via `uv run`/`uvx`",
    "persistence": "modelagem do banco: schema, índice por CEP e carga idempotente",
    "tests": "suíte de testes (pytest) cobre ETL/consulta/erros e passa",
    "error_handling": "tratamento de CEP inválido, CEP não encontrado e base DNE ausente",
    "architecture": "arquitetura e organização do código (modularidade, separação de camadas)",
    "production": "preparação para produção (CI, README, lint/ruff, empacotamento)",
    "git": "interação com Git/GitHub: commits significativos, tag semver e push",
}

# Descrição das colunas não-dimensionais.
META_COLUMNS = [
    ("#", "posição no ranking (ordenado pelo Subtotal)"),
    ("Harness", "o code agent que dirigiu o modelo (ex.: `claude_code`, `copilot_cli`)"),
    ("Modelo", "modelo avaliado; tag `· 1M` quando rodou em contexto de 1M"),
    ("Subtotal", "soma ponderada das 9 dimensões (0–100, **antes** dos modificadores) — "
                 "critério de ordenação"),
    ("Score", "Subtotal + modificadores (bônus de performance, penalidades), com teto 100"),
    ("Tier", "faixa do Score: A (80+), B (60–79), C (40–59), D (<40)"),
    ("Custo (US$)", "custo-equivalente estimado das fases (referência; o consumo conta no plano)"),
    ("Diverg.", "dimensões com divergência grande entre os juízes (sinalizadas p/ revisão)"),
]


def _legend_lines() -> list[str]:
    lines = ["### Legenda das colunas", ""]
    for name, desc in META_COLUMNS[:6]:
        lines.append(f"- **{name}** — {desc}")
    lines.append("")
    lines.append("Dimensões avaliadas (nota 0–100 por dimensão · peso na rubrica):")
    lines.append("")
    for dim in DIMENSIONS:
        lines.append(f"- **{DIM_LABELS[dim]}** (peso {WEIGHTS[dim]}) — {DIM_DESCRIPTIONS[dim]}")
    lines.append("")
    for name, desc in META_COLUMNS[6:]:
        lines.append(f"- **{name}** — {desc}")
    lines.append("")
    return lines


def _load_scores(cfg: Config) -> list[dict]:
    rows = []
    if not cfg.results_dir.exists():
        return rows
    for scores_file in sorted(cfg.results_dir.glob("*/scores.json")):
        try:
            row = json.loads(scores_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        row["_total_cost"] = _read_cost(cfg, scores_file.parent)
        rows.append(row)
    return rows


def _read_cost(cfg: Config, results_slug_dir) -> float | None:
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
        logs_dir = cfg.runs_dir / results_slug_dir.name / "logs"
        for pf in sorted(logs_dir.glob("phase*.json")) if logs_dir.exists() else []:
            try:
                c = json.loads(pf.read_text(encoding="utf-8")).get("cost_usd")
                if c:
                    costs.append(c)
            except json.JSONDecodeError:
                continue
    return round(sum(costs), 3) if costs else None


def build_leaderboard(cfg: Config) -> str:
    rows = _load_scores(cfg)
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

    lines += _legend_lines()

    header = "| # | Harness | Modelo | Subtotal | Score | Tier | " + \
        " | ".join(DIM_LABELS[d] for d in DIMENSIONS) + " | Custo (US$) | Diverg. |"
    sep = "|" + "---|" * (6 + len(DIMENSIONS) + 2)
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
        # nome limpo de exibição; tag de contexto SÓ para modelos 1M
        cand = cfg.candidate_by_slug(r.get("slug", ""))
        model_label = (cand.display if cand and cand.display else r.get("model", "?"))
        if cand and cand.context and cand.context.upper() == "1M":
            model_label = f"{model_label} · 1M"
        lines.append(
            f"| {i} | {r.get('agent','?')} | {model_label} | "
            f"**{sc.get('weighted_subtotal','?')}** | {sc.get('final_score','?')} | "
            f"{sc.get('tier','?')} | {dim_cells} | {cost} | {diverg} |"
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


README_START = "<!-- LEADERBOARD:START -->"
README_END = "<!-- LEADERBOARD:END -->"


def update_readme(cfg: Config) -> bool:
    """Injeta o leaderboard no README.md entre os marcadores. Retorna True se atualizou."""
    from benchmark.harness.config import REPO_ROOT

    readme = REPO_ROOT / "README.md"
    if not readme.exists():
        return False
    text = readme.read_text(encoding="utf-8")
    if README_START not in text or README_END not in text:
        return False
    table = build_leaderboard(cfg)
    # remove o H1 "# Leaderboard ..." (a seção "## Ranking atual" do README já encabeça)
    lines = table.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    table = "\n".join(lines)
    block = f"{README_START}\n\n{table}\n{README_END}"
    before = text.split(README_START)[0]
    after = text.split(README_END)[1]
    readme.write_text(before + block + after, encoding="utf-8")
    return True


def write_leaderboard(cfg: Config) -> Path:
    content = build_leaderboard(cfg)
    out = cfg.results_dir / "leaderboard.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    update_readme(cfg)
    return out
