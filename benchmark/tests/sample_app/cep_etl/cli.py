"""CLI `cep-etl`: load, query, serve."""

from __future__ import annotations

import json

import typer

from cep_etl.etl import DneError
from cep_etl.etl import load as etl_load
from cep_etl.query import lookup_many

app = typer.Typer(add_completion=False, help="ETL e consulta da base CEP dos Correios.")


@app.command()
def load():
    """Roda o ETL: lê DNE_PATH e popula o banco (DB_PATH)."""
    try:
        counts = etl_load()
    except DneError as e:
        typer.echo(f"Erro de DNE: {e}", err=True)
        raise typer.Exit(2) from None
    typer.echo(f"Carga concluída: {counts}")


@app.command()
def query(
    ceps: list[str] = typer.Argument(..., help="um ou mais CEPs"),
    as_json: bool = typer.Option(False, "--json", help="saída em JSON"),
):
    """Consulta um ou mais CEPs."""
    results = lookup_many(ceps)
    if as_json:
        typer.echo(json.dumps(results, ensure_ascii=False))
    else:
        for r in results:
            if r.get("erro"):
                typer.echo(f"{r.get('cep','?')}: {r['erro']}")
            else:
                typer.echo(
                    f"{r['cep']}: {r.get('tipo_logradouro','')} {r.get('logradouro','')} "
                    f"- {r.get('bairro','')} - {r.get('localidade','')}/{r.get('uf','')}".strip()
                )
    # se houver CEP com formato inválido, sinaliza via código de saída
    invalid = [r for r in results
               if isinstance(r.get("erro"), str) and "inválido" in r["erro"].lower()]
    if invalid and len(invalid) == len(results):
        raise typer.Exit(2)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="host"),
    port: int = typer.Option(8000, help="porta"),
):
    """Sobe a API REST + interface Web."""
    import uvicorn

    uvicorn.run("cep_etl.web:app", host=host, port=port, log_level="warning")


if __name__ == "__main__":
    app()
