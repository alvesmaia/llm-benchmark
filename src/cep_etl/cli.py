"""CLI do cep-etl: comandos load, query e serve."""

import json
import sys

import click

from .etl import run_etl
from .query import query_ceps, result_to_dict


@click.group()
def main():
    """ETL e consulta da base de CEP dos Correios (eDNE Básico)."""


@main.command()
@click.option("--dne-path", envvar="DNE_PATH", default=None,
              help="Caminho para a pasta com os arquivos LOG_*.TXT.")
@click.option("--db-path", envvar="DB_PATH", default=None,
              help="Caminho para o banco SQLite (padrão: cep.db).")
def load(dne_path, db_path):
    """Executa o ETL: lê os arquivos DNE e carrega no banco SQLite."""
    try:
        click.echo("Iniciando carga do eDNE Básico...")
        counts = run_etl(dne_path=dne_path, db_path=db_path)
        click.echo(f"  Localidades carregadas : {counts['localidades']:,}")
        click.echo(f"  Bairros carregados     : {counts['bairros']:,}")
        click.echo(f"  Logradouros carregados : {counts['logradouros']:,}")
        click.echo("Carga concluída com sucesso.")
    except (OSError, FileNotFoundError) as exc:
        click.echo(f"Erro: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Erro inesperado: {exc}", err=True)
        sys.exit(1)


@main.command()
@click.argument("ceps", nargs=-1, required=True)
@click.option("--json", "output_json", is_flag=True, default=False,
              help="Saída em formato JSON.")
@click.option("--db-path", envvar="DB_PATH", default=None,
              help="Caminho para o banco SQLite.")
def query(ceps, output_json, db_path):
    """Consulta um ou mais CEPs no banco de dados.

    Exemplos:\n
        cep-etl query 01001000\n
        cep-etl query 01001-000 20040-002 --json
    """
    try:
        results = query_ceps(list(ceps), db_path=db_path)
    except Exception as exc:
        click.echo(f"Erro ao consultar banco: {exc}", err=True)
        sys.exit(1)

    if output_json:
        click.echo(json.dumps([result_to_dict(r) for r in results], ensure_ascii=False, indent=2))
        return

    for r in results:
        d = result_to_dict(r)
        if not d["found"]:
            click.echo(f"CEP {d['cep']}: {d['error']}")
        else:
            parts = []
            if d["tipo_logradouro"] and d["logradouro"]:
                parts.append(f"{d['tipo_logradouro']} {d['logradouro']}")
            if d["bairro"]:
                parts.append(d["bairro"])
            parts.append(d["localidade"])
            parts.append(f"{d['uf']} — CEP {d['cep']}")
            click.echo(", ".join(parts))


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Host do servidor.")
@click.option("--port", default=8000, show_default=True, help="Porta do servidor.")
@click.option("--reload", is_flag=True, default=False, help="Modo de recarga automática.")
@click.option("--db-path", envvar="DB_PATH", default=None,
              help="Caminho para o banco SQLite.")
def serve(host, port, reload, db_path):
    """Inicia o servidor Web + API REST."""
    import os

    import uvicorn

    if db_path:
        os.environ["DB_PATH"] = db_path

    uvicorn.run(
        "cep_etl.api:app",
        host=host,
        port=port,
        reload=reload,
    )
