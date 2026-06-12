"""Módulo ETL: leitura e carga dos arquivos eDNE Básico dos Correios."""

import os
import sqlite3
from pathlib import Path

from .db import get_connection, init_schema

ENCODING = "latin-1"
SEP = "@"


def _get_dne_path() -> Path:
    dne_path = os.environ.get("DNE_PATH")
    if not dne_path:
        raise OSError(
            "Variável de ambiente DNE_PATH não definida. "
            "Defina DNE_PATH com o caminho para a pasta com os arquivos LOG_*.TXT."
        )
    path = Path(dne_path)
    if not path.is_dir():
        raise FileNotFoundError(
            f"DNE_PATH '{dne_path}' não é um diretório válido ou não existe."
        )
    return path


def _check_required_files(dne_path: Path) -> None:
    required = ["LOG_LOCALIDADE.TXT", "LOG_BAIRRO.TXT"]
    missing = [f for f in required if not (dne_path / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"Arquivos obrigatórios não encontrados em '{dne_path}': {', '.join(missing)}"
        )
    logradouro_files = list(dne_path.glob("LOG_LOGRADOURO_*.TXT"))
    if not logradouro_files:
        raise FileNotFoundError(
            f"Nenhum arquivo LOG_LOGRADOURO_*.TXT encontrado em '{dne_path}'."
        )


def _read_file(path: Path):
    with open(path, encoding=ENCODING, errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if line:
                yield line.split(SEP)


def _load_localidades(conn: sqlite3.Connection, dne_path: Path) -> int:
    path = dne_path / "LOG_LOCALIDADE.TXT"
    rows = []
    for fields in _read_file(path):
        if len(fields) < 9:
            continue
        rows.append((
            int(fields[0]),   # loc_nu
            fields[1].strip(),  # ufe_sg
            fields[2].strip(),  # loc_no
            fields[3].strip() or None,  # cep
            fields[4].strip(),  # loc_in_sit
            fields[5].strip(),  # loc_in_tipo
            int(fields[6]) if fields[6].strip() else None,  # loc_nu_sub
            fields[7].strip() or None,  # loc_no_abrev
            fields[8].strip() or None,  # mun_nu
        ))

    conn.executemany("""
        INSERT OR REPLACE INTO localidades
            (loc_nu, ufe_sg, loc_no, cep, loc_in_sit, loc_in_tipo, loc_nu_sub, loc_no_abrev, mun_nu)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    return len(rows)


def _load_bairros(conn: sqlite3.Connection, dne_path: Path) -> int:
    path = dne_path / "LOG_BAIRRO.TXT"
    rows = []
    for fields in _read_file(path):
        if len(fields) < 5:
            continue
        rows.append((
            int(fields[0]),    # bai_nu
            fields[1].strip(), # ufe_sg
            int(fields[2]),    # loc_nu
            fields[3].strip(), # bai_no
            fields[4].strip() or None,  # bai_no_abrev
        ))

    conn.executemany("""
        INSERT OR REPLACE INTO bairros (bai_nu, ufe_sg, loc_nu, bai_no, bai_no_abrev)
        VALUES (?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    return len(rows)


def _load_logradouros(conn: sqlite3.Connection, dne_path: Path) -> int:
    total = 0
    logradouro_files = sorted(dne_path.glob("LOG_LOGRADOURO_*.TXT"))

    for path in logradouro_files:
        rows = []
        for fields in _read_file(path):
            if len(fields) < 11:
                continue
            rows.append((
                int(fields[0]),    # log_nu
                fields[1].strip(), # ufe_sg
                int(fields[2]),    # loc_nu
                int(fields[3]) if fields[3].strip() else None,  # bai_nu_ini
                int(fields[4]) if fields[4].strip() else None,  # bai_nu_fim
                fields[5].strip(), # log_no
                fields[6].strip() or None,  # log_complemento
                fields[7].strip() or None,  # cep
                fields[8].strip() or None,  # tlo_tx
                fields[9].strip() or None,  # log_sta_tlo
                fields[10].strip() or None, # log_no_abrev
            ))

        conn.executemany("""
            INSERT OR REPLACE INTO logradouros
                (log_nu, ufe_sg, loc_nu, bai_nu_ini, bai_nu_fim, log_no,
                 log_complemento, cep, tlo_tx, log_sta_tlo, log_no_abrev)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        total += len(rows)

    return total


def run_etl(dne_path: str | None = None, db_path: str | None = None) -> dict:
    """Executa o ETL completo: lê os arquivos DNE e carrega no banco.

    Retorna dict com contagens de registros carregados.
    """
    if dne_path:
        base_path = Path(dne_path)
    else:
        base_path = _get_dne_path()

    _check_required_files(base_path)

    conn = get_connection(db_path)
    try:
        init_schema(conn)
        n_loc = _load_localidades(conn, base_path)
        n_bai = _load_bairros(conn, base_path)
        n_log = _load_logradouros(conn, base_path)
    finally:
        conn.close()

    return {
        "localidades": n_loc,
        "bairros": n_bai,
        "logradouros": n_log,
    }
