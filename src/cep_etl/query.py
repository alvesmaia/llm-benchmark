"""Lógica de consulta de CEP com fallback para localidade."""

import re
import sqlite3
from dataclasses import dataclass

from .db import db_connection


@dataclass
class CepResult:
    cep: str
    logradouro: str | None
    tipo_logradouro: str | None
    complemento: str | None
    bairro: str | None
    localidade: str
    uf: str
    fonte: str  # "logradouro" | "localidade"


@dataclass
class CepNotFound:
    cep: str
    erro: str


def normalize_cep(cep: str) -> str:
    """Remove formatação e valida o CEP."""
    digits = re.sub(r"\D", "", cep)
    if len(digits) != 8:
        raise ValueError(
            f"CEP '{cep}' inválido: deve ter 8 dígitos numéricos (com ou sem hífen)."
        )
    return digits


def _query_logradouro(conn: sqlite3.Connection, cep: str) -> sqlite3.Row | None:
    row = conn.execute(
        """
        SELECT
            l.cep,
            l.log_no,
            l.tlo_tx,
            l.log_complemento,
            b.bai_no,
            loc.loc_no,
            loc.ufe_sg
        FROM logradouro l
        LEFT JOIN bairro b ON b.bai_nu = l.bai_nu_ini
        LEFT JOIN localidade loc ON loc.loc_nu = l.loc_nu
        WHERE l.cep = ?
        LIMIT 1
        """,
        (cep,),
    ).fetchone()
    return row


def _query_localidade(conn: sqlite3.Connection, cep: str) -> sqlite3.Row | None:
    row = conn.execute(
        """
        SELECT cep, loc_no, ufe_sg
        FROM localidade
        WHERE cep = ?
        LIMIT 1
        """,
        (cep,),
    ).fetchone()
    return row


def query_cep(cep_raw: str, db_path: str | None = None) -> CepResult | CepNotFound:
    """Consulta um único CEP. Retorna CepResult ou CepNotFound."""
    try:
        cep = normalize_cep(cep_raw)
    except ValueError as e:
        return CepNotFound(cep=cep_raw, erro=str(e))

    with db_connection(db_path) as conn:
        row = _query_logradouro(conn, cep)
        if row:
            return CepResult(
                cep=row["cep"],
                logradouro=row["log_no"],
                tipo_logradouro=row["tlo_tx"],
                complemento=row["log_complemento"] or None,
                bairro=row["bai_no"],
                localidade=row["loc_no"],
                uf=row["ufe_sg"],
                fonte="logradouro",
            )

        row = _query_localidade(conn, cep)
        if row:
            return CepResult(
                cep=row["cep"],
                logradouro=None,
                tipo_logradouro=None,
                complemento=None,
                bairro=None,
                localidade=row["loc_no"],
                uf=row["ufe_sg"],
                fonte="localidade",
            )

    return CepNotFound(cep=cep, erro=f"CEP '{cep}' não encontrado.")


def query_ceps(ceps: list[str], db_path: str | None = None) -> list[CepResult | CepNotFound]:
    """Consulta múltiplos CEPs em lote."""
    return [query_cep(cep, db_path) for cep in ceps]


def result_to_dict(result: CepResult | CepNotFound) -> dict:
    """Converte resultado para dicionário serializável."""
    if isinstance(result, CepNotFound):
        return {"cep": result.cep, "erro": result.erro, "encontrado": False}
    return {
        "cep": result.cep,
        "logradouro": result.logradouro,
        "tipo_logradouro": result.tipo_logradouro,
        "complemento": result.complemento,
        "bairro": result.bairro,
        "localidade": result.localidade,
        "uf": result.uf,
        "fonte": result.fonte,
        "encontrado": True,
    }
