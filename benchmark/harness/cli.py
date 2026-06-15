"""CLI `bench` — ponto de entrada do harness (uv run bench ...)."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from benchmark.harness import export as export_mod
from benchmark.harness import report as report_mod
from benchmark.harness import run_benchmark
from benchmark.harness import serve as serve_mod
from benchmark.harness.config import load_config
from benchmark.harness.scenarios.registry import get_scenario

app = typer.Typer(add_completion=False,
                  help="Benchmark de LLMs como code agents (Gestão de Ativos de TI, 3 fases).")
console = Console()


@app.command()
def run(
    only: str = typer.Option(None, help="slug(s) separados por vírgula (ex.: claude_code-sonnet)"),
    config: str = typer.Option(None, help="caminho do config.yaml"),
    scenario: str = typer.Option("it_assets", help="cenário (único: it_assets)"),
    skip_agent: bool = typer.Option(
        False, "--skip-agent",
        help="não rebuilda: re-roda checagens + juízes no app já construído"),
    export: bool = typer.Option(
        True, "--export/--no-export",
        help="gera um ZIP (app + prompt do juiz + resultados) por candidato ao final"),
):
    """Roda a matriz de candidatos (3 fases) e pontua cada um."""
    cfg = load_config(config)
    sc = get_scenario(scenario)
    only_list = [s.strip() for s in only.split(",")] if only else None
    results = run_benchmark.run_matrix(cfg, only=only_list, skip_agent=skip_agent, scenario=sc)
    for r in results:
        score = r["score"]
        console.print(f"[bold]{r['slug']}[/bold]: {score['final_score']} (Tier {score['tier']})")
        if export:
            zip_path = export_mod.export_candidate(cfg, r["slug"], sc)
            console.print(f"  [dim]ZIP:[/dim] {zip_path}")
    out = report_mod.write_leaderboard(cfg, sc)
    console.print(f"[green]Leaderboard atualizado:[/green] {out}")


@app.command()
def selftest(
    config: str = typer.Option(None, help="caminho do config.yaml"),
    scenario: str = typer.Option("it_assets", help="cenário (único: it_assets)"),
):
    """Valida o pipeline contra a fixture + sample_app, sem chamar agentes pagos."""
    cfg = load_config(config)
    out = run_benchmark.selftest(cfg, get_scenario(scenario))
    _print_objective(out["objective"])
    sc = out["score"]
    console.print(f"\n[bold]Score (só objetivo):[/bold] {sc['final_score']} — Tier {sc['tier']}")
    # critério de sanidade do self-test: o sample_app deve atingir pelo menos Tier B
    if sc["final_score"] < 60:
        console.print("[red]FALHA: sample_app deveria pontuar >= 60 (Tier B).[/red]")
        raise typer.Exit(1)
    console.print("[green]Self-test OK.[/green]")


@app.command()
def rescore(
    slug: str = typer.Argument(..., help="slug do candidato (ex.: claude_code-sonnet)"),
    config: str = typer.Option(None, help="caminho do config.yaml"),
    scenario: str = typer.Option("it_assets", help="cenário (único: it_assets)"),
):
    """Recalcula o score de um candidato já avaliado: re-roda as checagens objetivas no app
    existente e reaproveita as notas dos juízes (não rebuilda nem chama juízes de novo)."""
    cfg = load_config(config)
    sc_obj = get_scenario(scenario)
    out = run_benchmark.rescore(cfg, slug, sc_obj)
    _print_objective(out["objective"])
    sc = out["score"]
    console.print(f"\n[bold]{slug}:[/bold] {sc['final_score']} — Tier {sc['tier']}")
    leaderboard = report_mod.write_leaderboard(cfg, sc_obj)
    console.print(f"[green]Leaderboard atualizado:[/green] {leaderboard}")


@app.command()
def score(
    config: str = typer.Option(None, help="caminho do config.yaml"),
    scenario: str = typer.Option("it_assets", help="cenário (único: it_assets)"),
):
    """Reconstrói o leaderboard a partir dos results/<slug>/scores.json já existentes."""
    cfg = load_config(config)
    out = report_mod.write_leaderboard(cfg, get_scenario(scenario))
    console.print(f"[green]Leaderboard:[/green] {out}")


@app.command()
def report(
    config: str = typer.Option(None, help="caminho do config.yaml"),
    scenario: str = typer.Option("it_assets", help="cenário (único: it_assets)"),
):
    """Alias de `score`: regenera o leaderboard."""
    cfg = load_config(config)
    out = report_mod.write_leaderboard(cfg, get_scenario(scenario))
    console.print(out.read_text(encoding="utf-8"))


@app.command()
def export(
    slug: str = typer.Argument(..., help="slug do candidato (ex.: opencode-sonnet)"),
    config: str = typer.Option(None, help="caminho do config.yaml"),
    scenario: str = typer.Option("it_assets", help="cenário (único: it_assets)"),
    output: str = typer.Option(None, help="diretório de saída (default: exports/<scenario>/)"),
):
    """Gera um ZIP com o projeto gerado + o prompt do juiz + os resultados, para reavaliação
    por um juiz externo (reaproveita o mesmo prompt usado pelo painel interno)."""
    from pathlib import Path

    cfg = load_config(config)
    sc = get_scenario(scenario)
    out_dir = Path(output) if output else None
    zip_path = export_mod.export_candidate(cfg, slug, sc, out_dir=out_dir)
    console.print(f"[green]Exportado:[/green] {zip_path}")


@app.command()
def serve(
    slug: str = typer.Argument(..., help="slug do candidato (ex.: claude_code-opus-4-8)"),
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000),
    config: str = typer.Option(None),
    scenario: str = typer.Option("it_assets", help="cenário (único: it_assets)"),
):
    """Sobe Web+API do projeto gerado por um candidato (um único comando `uvx`/`uv run`)."""
    cfg = load_config(config)
    raise typer.Exit(serve_mod.serve(cfg, slug, host=host, port=port,
                                     scenario=get_scenario(scenario)))


def _print_objective(objective: dict) -> None:
    table = Table(title="Checagens objetivas")
    table.add_column("check")
    table.add_column("dim")
    table.add_column("nota", justify="right")
    table.add_column("detalhe")
    for c in objective["checks"]:
        table.add_row(c["id"], c["dimension"], str(c["note"]), c["detail"][:60])
    console.print(table)
    console.print("Por dimensão (objetivo):",
                  json.dumps(objective["objective_by_dimension"], ensure_ascii=False))
    console.print("Flags:", json.dumps(objective["flags"], ensure_ascii=False))


if __name__ == "__main__":
    app()
