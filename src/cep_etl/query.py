"""Módulo de consulta: busca de CEPs no banco de dados."""

import re
import sqlite3
from dataclasses import dataclass

from .db import get_connection

CEP_RE = re.compile(r"^\d{8}$")


def normalize_cep(cep: str) -> str:
    """Remove máscara do CEP e valida formato."""
    cleaned = re.sub(r"[-.\s]", "", cep.strip())
    if not CEP_RE.match(cleaned):
        raise ValueError(
            f"CEP inválido: '{cep}'. O CEP deve conter exatamente 8 dígitos numéricos."
        )
    return cleaned


@dataclass
class CepResult:
    cep: str
    logradouro: str | None
    tipo_logradouro: str | None
    bairro: str | None
    localidade: str
    uf: str
    found: bool = True
    source: str = "logradouro"  # "logradouro" | "localidade"


@dataclass
class CepNotFound:
    cep: str
    found: bool = False
    error: str = "CEP não encontrado"


def _query_logradouro(conn: sqlite3.Connection, cep: str) -> CepResult | None:
    row = conn.execute("""
        SELECT
            l.cep,
            l.log_no,
            l.tlo_tx,
            b.bai_no,
            loc.loc_no,
            loc.ufe_sg
        FROM logradouros l
        JOIN localidades loc ON loc.loc_nu = l.loc_nu
        LEFT JOIN bairros b ON b.bai_nu = l.bai_nu_ini
        WHERE l.cep = ?
        LIMIT 1
    """, (cep,)).fetchone()

    if row:
        return CepResult(
            cep=row[0],
            logradouro=row[1],
            tipo_logradouro=row[2],
            bairro=row[3],
            localidade=row[4],
            uf=row[5],
            found=True,
            source="logradouro",
        )
    return None


def _query_localidade(conn: sqlite3.Connection, cep: str) -> CepResult | None:
    row = conn.execute("""
        SELECT cep, loc_no, ufe_sg
        FROM localidades
        WHERE cep = ?
        LIMIT 1
    """, (cep,)).fetchone()

    if row:
        return CepResult(
            cep=row[0],
            logradouro=None,
            tipo_logradouro=None,
            bairro=None,
            localidade=row[1],
            uf=row[2],
            found=True,
            source="localidade",
        )
    return None


def query_cep(cep: str, db_path: str | None = None) -> CepResult | CepNotFound:
    """Consulta um único CEP no banco de dados."""
    try:
        normalized = normalize_cep(cep)
    except ValueError as exc:
        return CepNotFound(cep=cep, error=str(exc))

    conn = get_connection(db_path)
    try:
        result = _query_logradouro(conn, normalized)
        if result is None:
            result = _query_localidade(conn, normalized)
        if result is None:
            return CepNotFound(cep=normalized)
        return result
    finally:
        conn.close()


def query_ceps(ceps: list[str], db_path: str | None = None) -> list[CepResult | CepNotFound]:
    """Consulta múltiplos CEPs, retornando resultado para cada um."""
    conn = get_connection(db_path)
    try:
        results = []
        for cep in ceps:
            try:
                normalized = normalize_cep(cep)
            except ValueError as exc:
                results.append(CepNotFound(cep=cep, error=str(exc)))
                continue

            result = _query_logradouro(conn, normalized)
            if result is None:
                result = _query_localidade(conn, normalized)
            if result is None:
                results.append(CepNotFound(cep=normalized))
            else:
                results.append(result)
        return results
    finally:
        conn.close()


def result_to_dict(r: CepResult | CepNotFound) -> dict:
    """Serializa resultado para dicionário."""
    if isinstance(r, CepNotFound):
        return {"cep": r.cep, "found": False, "error": r.error}
    return {
        "cep": r.cep,
        "logradouro": r.logradouro,
        "tipo_logradouro": r.tipo_logradouro,
        "bairro": r.bairro,
        "localidade": r.localidade,
        "uf": r.uf,
        "found": True,
        "source": r.source,
    }
