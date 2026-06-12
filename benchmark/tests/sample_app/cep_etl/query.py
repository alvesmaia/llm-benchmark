"""Consulta de CEP com validação e fallback para CEP de localidade."""

from __future__ import annotations

from cep_etl.db import connect


class CepInvalidoError(ValueError):
    """CEP com formato inválido."""


def normalize_cep(cep: str) -> str:
    digits = "".join(ch for ch in str(cep) if ch.isdigit())
    if len(digits) != 8:
        raise CepInvalidoError(f"CEP inválido: {cep!r} (esperado 8 dígitos)")
    return digits


def lookup(cep: str) -> dict | None:
    """Retorna o endereço do CEP, ou None se não achar. Levanta CepInvalidoError se inválido."""
    digits = normalize_cep(cep)
    con = connect()
    try:
        row = con.execute(
            """SELECT l.cep, l.nome AS logradouro, l.tipo AS tipo_logradouro, l.abrev,
                      b.nome AS bairro, loc.nome AS localidade, loc.uf AS uf
               FROM logradouro l
               LEFT JOIN bairro b ON b.bai_nu = l.bai_nu
               LEFT JOIN localidade loc ON loc.loc_nu = l.loc_nu
               WHERE l.cep = ?""",
            (digits,),
        ).fetchone()
        if row:
            return {
                "cep": row["cep"], "logradouro": row["logradouro"],
                "tipo_logradouro": row["tipo_logradouro"], "bairro": row["bairro"],
                "localidade": row["localidade"], "uf": row["uf"],
            }

        # fallback: CEP de localidade (município/UF)
        loc = con.execute(
            "SELECT cep, nome AS localidade, uf FROM localidade WHERE cep = ?",
            (digits,),
        ).fetchone()
        if loc:
            return {"cep": loc["cep"], "localidade": loc["localidade"], "uf": loc["uf"]}
        return None
    finally:
        con.close()


def lookup_many(ceps: list[str]) -> list[dict]:
    """Consulta em lote. CEP inválido/não encontrado vira entrada com 'erro', sem quebrar o lote."""
    results = []
    for cep in ceps:
        try:
            found = lookup(cep)
        except CepInvalidoError as e:
            results.append({"cep": cep, "erro": str(e)})
            continue
        if found is None:
            digits = "".join(c for c in cep if c.isdigit())
            results.append({"cep": digits, "erro": "não encontrado"})
        else:
            results.append(found)
    return results
