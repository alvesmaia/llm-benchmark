"""Interface de linha de comando (CLI) para o ETL de CEP."""

import json
import sys

import click

from .etl import run_etl
from .query import CepNotFound, query_ceps, result_to_dict


@click.group()
def main():
    """ETL e consulta da base de CEP dos Correios (eDNE Básico)."""


@main.command()
@click.option("--db-path", envvar="DB_PATH", default=None, help="Caminho do banco SQLite.")
@click.option("--dne-path", envvar="DNE_PATH", default=None, help="Pasta com os arquivos LOG_*.TXT.")
def load(db_path, dne_path):
    """Carrega os dados eDNE no banco de dados."""
    try:
        click.echo("Iniciando ETL...")
        result = run_etl(db_path=db_path, dne_path=dne_path)
        click.echo(
            f"ETL concluído: {result['localidades']} localidades, "
            f"{result['bairros']} bairros, "
            f"{result['logradouros']} logradouros."
        )
    except RuntimeError as e:
        click.echo(f"Erro: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("ceps", nargs=-1, required=True)
@click.option("--db-path", envvar="DB_PATH", default=None, help="Caminho do banco SQLite.")
@click.option("--json", "output_json", is_flag=True, help="Saída em formato JSON.")
def query(ceps, db_path, output_json):
    """Consulta um ou mais CEPs. Ex: cep-etl query 01001-000 20040002"""
    try:
        results = query_ceps(list(ceps), db_path=db_path)
    except Exception as e:
        click.echo(f"Erro ao consultar banco: {e}", err=True)
        sys.exit(1)

    if output_json:
        click.echo(json.dumps([result_to_dict(r) for r in results], ensure_ascii=False, indent=2))
        return

    has_error = False
    for result in results:
        if isinstance(result, CepNotFound):
            click.echo(f"[NÃO ENCONTRADO] {result.erro}")
            has_error = True
        else:
            parts = [f"CEP: {result.cep}"]
            if result.tipo_logradouro and result.logradouro:
                parts.append(f"Logradouro: {result.tipo_logradouro} {result.logradouro}")
            elif result.logradouro:
                parts.append(f"Logradouro: {result.logradouro}")
            if result.complemento:
                parts.append(f"Complemento: {result.complemento}")
            if result.bairro:
                parts.append(f"Bairro: {result.bairro}")
            parts.append(f"Localidade: {result.localidade}/{result.uf}")
            click.echo(" | ".join(parts))

    if has_error:
        sys.exit(1)


@main.command()
@click.option("--host", default="0.0.0.0", help="Host do servidor.", show_default=True)
@click.option("--port", default=8000, help="Porta do servidor.", show_default=True)
@click.option("--reload", is_flag=True, help="Habilitar auto-reload (desenvolvimento).")
def serve(host, port, reload):
    """Inicia o servidor web com API REST e interface web."""
    import uvicorn

    click.echo(f"Iniciando servidor em http://{host}:{port}")
    uvicorn.run(
        "cep_etl.api:app",
        host=host,
        port=port,
        reload=reload,
    )
