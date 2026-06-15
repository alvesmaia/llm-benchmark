"""CLI `it-assets` — console script (executável por `uvx --from . it-assets ...`)."""

from __future__ import annotations

import sys

import typer

from it_assets.config import settings

app = typer.Typer(add_completion=False, help="Gestão de movimentação de ativos de TI.")


@app.command(name="import")
def import_data() -> None:
    """Carrega o SQLite a partir de DATASET_PATH (idempotente)."""
    from it_assets.ingest import ensure_loaded

    try:
        n = ensure_loaded()
    except FileNotFoundError:
        typer.secho(
            f"erro: base não encontrada em {settings.dataset_path}", fg="red", err=True
        )
        raise typer.Exit(1) from None
    typer.echo(f"carregadas {n} movimentações em {settings.db_path}")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Sobe a API REST + Web (FastAPI/uvicorn)."""
    import uvicorn

    uvicorn.run("it_assets.web:app", host=host, port=port, log_level="warning")


def main() -> None:
    try:
        app()
    except FileNotFoundError as e:
        print(f"erro: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
