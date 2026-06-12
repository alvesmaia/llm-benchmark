"""CLI `bench` — ponto de entrada do harness (uv run bench ...)."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from benchmark.harness import report as report_mod
from benchmark.harness import run_benchmark
from benchmark.harness import serve as serve_mod
from benchmark.harness.config import load_config

app = typer.Typer(add_completion=False,
                  help="Benchmark de LLMs como code agents (desafio ETL CEP).")
console = Console()


@app.command()
def run(
    only: str = typer.Option(None, help="slug(s) separados por vírgula (ex.: claude_code-opus)"),
    config: str = typer.Option(None, help="caminho do config.yaml"),
):
    """Roda a matriz de candidatos (3 fases) e pontua cada um."""
    cfg = load_config(config)
    only_list = [s.strip() for s in only.split(",")] if only else None
    results = run_benchmark.run_matrix(cfg, only=only_list)
    for r in results:
        sc = r["score"]
        console.print(f"[bold]{r['slug']}[/bold]: {sc['final_score']} (Tier {sc['tier']})")
    report_mod.write_leaderboard(cfg)
    console.print(f"[green]Leaderboard atualizado:[/green] {cfg.results_dir / 'leaderboard.md'}")


@app.command()
def selftest(
    config: str = typer.Option(None, help="caminho do config.yaml"),
):
    """Valida o pipeline contra a fixture + sample_app, sem chamar agentes pagos."""
    cfg = load_config(config)
    out = run_benchmark.selftest(cfg)
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
):
    """Recalcula o score de um candidato já avaliado: re-roda as checagens objetivas no app
    existente e reaproveita as notas dos juízes (não rebuilda nem chama juízes de novo)."""
    cfg = load_config(config)
    out = run_benchmark.rescore(cfg, slug)
    _print_objective(out["objective"])
    sc = out["score"]
    console.print(f"\n[bold]{slug}:[/bold] {sc['final_score']} — Tier {sc['tier']}")
    report_mod.write_leaderboard(cfg)
    console.print(f"[green]Leaderboard atualizado:[/green] {cfg.results_dir / 'leaderboard.md'}")


@app.command()
def score(config: str = typer.Option(None, help="caminho do config.yaml")):
    """Reconstrói o leaderboard a partir dos results/<slug>/scores.json já existentes."""
    cfg = load_config(config)
    out = report_mod.write_leaderboard(cfg)
    console.print(f"[green]Leaderboard:[/green] {out}")


@app.command()
def report(config: str = typer.Option(None, help="caminho do config.yaml")):
    """Alias de `score`: regenera o leaderboard."""
    cfg = load_config(config)
    out = report_mod.write_leaderboard(cfg)
    console.print(out.read_text(encoding="utf-8"))


@app.command()
def serve(
    slug: str = typer.Argument(..., help="slug do candidato (ex.: claude_code-opus)"),
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000),
    config: str = typer.Option(None),
    load: bool = typer.Option(True, help="rodar o ETL antes de subir"),
):
    """Sobe Web+API do projeto gerado por um candidato (um único comando)."""
    cfg = load_config(config)
    raise typer.Exit(serve_mod.serve(cfg, slug, host=host, port=port, load_first=load))


@app.command()
def query(
    slug: str = typer.Argument(...),
    ceps: list[str] = typer.Argument(...),
    as_json: bool = typer.Option(False, "--json"),
    config: str = typer.Option(None),
):
    """Consulta CEP(s) usando o projeto gerado por um candidato."""
    cfg = load_config(config)
    raise typer.Exit(serve_mod.query(cfg, slug, ceps, as_json=as_json))


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
