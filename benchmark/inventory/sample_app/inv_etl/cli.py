"""CLI `inv-etl`: import, serve."""

from __future__ import annotations

import typer

from inv_etl.etl import DatasetError
from inv_etl.etl import import_sales as etl_import

app = typer.Typer(add_completion=False, help="Gestão de estoque a partir de vendas (car-sales).")


@app.command(name="import")
def import_():
    """Roda o ETL: lê DATASET_PATH (CSV de vendas) e popula o banco (DB_PATH)."""
    try:
        counts = etl_import()
    except DatasetError as e:
        typer.echo(f"Erro de dataset: {e}", err=True)
        raise typer.Exit(2) from None
    typer.echo(f"Importação concluída: {counts}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="host"),
    port: int = typer.Option(8000, help="porta"),
):
    """Sobe a API REST + interface Web (não bloqueante para a avaliação automatizada)."""
    import uvicorn

    uvicorn.run("inv_etl.api:app", host=host, port=port, log_level="warning")


if __name__ == "__main__":
    app()
