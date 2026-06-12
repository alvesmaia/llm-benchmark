"""Gera a fixture sintética da base DNE no formato eDNE Básico (delimitado por @, encoding Latin-1).

Rodar: uv run python benchmark/fixtures/_generate.py
Os arquivos gerados imitam LOG_LOCALIDADE.TXT, LOG_BAIRRO.TXT e LOG_LOGRADOURO_<UF>.TXT.
Contém acentos propositalmente para exercitar o encoding Latin-1.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent / "dne_sample"
ENC = "latin-1"

# LOC_NU @ UFE_SG @ LOC_NO @ CEP @ LOC_IN_SIT @ LOC_IN_TIPO_LOC @ LOC_NU_SUB @ LOC_NO_ABREV @ MUN_NU
LOCALIDADES = [
    ["1", "SP", "São Paulo", "", "0", "0", "", "S.Paulo", "3550308"],
    ["2", "RJ", "Rio de Janeiro", "", "0", "0", "", "R.Janeiro", "3304557"],
    ["3", "SP", "Campinas", "", "0", "0", "", "Campinas", "3509502"],
    # localidade com CEP único — exercita o fallback de CEP de localidade
    ["4", "MG", "Borda da Mata", "37564000", "1", "0", "", "Borda Mata", "3108503"],
]

# BAI_NU @ UFE_SG @ LOC_NU @ BAI_NO @ BAI_NO_ABREV
BAIRROS = [
    ["1", "SP", "1", "Sé", "Sé"],
    ["2", "SP", "1", "Bela Vista", "B.Vista"],
    ["3", "RJ", "2", "Centro", "Centro"],
    ["4", "SP", "3", "Centro", "Centro"],
]

# LOG_NU @ UFE_SG @ LOC_NU @ BAI_NU_INI @ BAI_NU_FIM @ LOG_NO @ LOG_COMPLEMENTO @ CEP @ TLO_TX @ LOG_STA_TLO @ LOG_NO_ABREV
LOGRADOUROS = {
    "SP": [
        ["1", "SP", "1", "1", "", "Praça da Sé", "lado ímpar", "01001000", "Praça", "S", "Pç da Sé"],
        ["2", "SP", "1", "2", "", "Avenida Paulista", "", "01310100", "Avenida", "S", "Av Paulista"],
        ["3", "SP", "3", "4", "", "Avenida Francisco Glicério", "", "13012100", "Avenida", "S", "Av Fco Glicério"],
    ],
    "RJ": [
        ["10", "RJ", "2", "3", "", "Avenida Rio Branco", "", "20040002", "Avenida", "S", "Av Rio Branco"],
    ],
}


def write_rows(path: Path, rows: list[list[str]]) -> None:
    text = "\n".join("@".join(r) for r in rows) + "\n"
    path.write_bytes(text.encode(ENC))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write_rows(OUT / "LOG_LOCALIDADE.TXT", LOCALIDADES)
    write_rows(OUT / "LOG_BAIRRO.TXT", BAIRROS)
    for uf, rows in LOGRADOUROS.items():
        write_rows(OUT / f"LOG_LOGRADOURO_{uf}.TXT", rows)

    # expected_queries.json (verdade para as checagens objetivas). Em Unicode/UTF-8.
    expected = {
        "found": {
            "01001000": {
                "cep": "01001000", "logradouro": "Praça da Sé", "tipo_logradouro": "Praça",
                "bairro": "Sé", "localidade": "São Paulo", "uf": "SP",
            },
            "01001-000": {
                "cep": "01001000", "logradouro": "Praça da Sé", "tipo_logradouro": "Praça",
                "bairro": "Sé", "localidade": "São Paulo", "uf": "SP",
            },
            "01310100": {
                "cep": "01310100", "logradouro": "Avenida Paulista", "tipo_logradouro": "Avenida",
                "bairro": "Bela Vista", "localidade": "São Paulo", "uf": "SP",
            },
            "20040002": {
                "cep": "20040002", "logradouro": "Avenida Rio Branco", "tipo_logradouro": "Avenida",
                "bairro": "Centro", "localidade": "Rio de Janeiro", "uf": "RJ",
            },
            "13012100": {
                "cep": "13012100", "logradouro": "Avenida Francisco Glicério", "tipo_logradouro": "Avenida",
                "bairro": "Centro", "localidade": "Campinas", "uf": "SP",
            },
            # fallback: CEP de localidade (sem logradouro/bairro)
            "37564000": {
                "cep": "37564000", "localidade": "Borda da Mata", "uf": "MG",
            },
        },
        "not_found": ["99999999"],
        "invalid": ["abc", "123", "0100100000"],
    }
    (Path(__file__).parent / "expected_queries.json").write_text(
        json.dumps(expected, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Fixture gerada em {OUT}")


if __name__ == "__main__":
    main()
