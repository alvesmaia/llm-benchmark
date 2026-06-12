"""ETL: leitura dos arquivos eDNE Básico e carga no banco de dados."""

import glob
import os
import sqlite3
from pathlib import Path

from .db import create_schema, db_connection

ENCODING = "latin-1"
SEP = "@"


def _get_dne_path() -> Path:
    dne_path = os.environ.get("DNE_PATH")
    if not dne_path:
        raise RuntimeError(
            "Variável de ambiente DNE_PATH não definida. "
            "Defina DNE_PATH apontando para a pasta com os arquivos LOG_*.TXT."
        )
    path = Path(dne_path)
    if not path.is_dir():
        raise RuntimeError(
            f"DNE_PATH='{dne_path}' não é um diretório válido ou não existe."
        )
    return path


def _read_file(file_path: Path) -> list[list[str]]:
    rows = []
    with open(file_path, encoding=ENCODING) as f:
        for line in f:
            line = line.rstrip("\n\r")
            if line:
                rows.append(line.split(SEP))
    return rows


def _load_localidades(conn: sqlite3.Connection, dne_path: Path) -> int:
    file_path = dne_path / "LOG_LOCALIDADE.TXT"
    if not file_path.exists():
        raise RuntimeError(f"Arquivo não encontrado: {file_path}")

    rows = _read_file(file_path)
    count = 0
    for row in rows:
        if len(row) < 9:
            row.extend([""] * (9 - len(row)))
        loc_nu, ufe_sg, loc_no, cep, loc_in_sit, loc_in_tipo, loc_nu_sub, loc_no_abrev, mun_nu = (
            row[0], row[1], row[2], row[3] or None, row[4], row[5],
            row[6] or None, row[7], row[8]
        )
        conn.execute(
            """
            INSERT INTO localidade
                (loc_nu, ufe_sg, loc_no, cep, loc_in_sit, loc_in_tipo, loc_nu_sub, loc_no_abrev, mun_nu)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(loc_nu) DO UPDATE SET
                ufe_sg=excluded.ufe_sg, loc_no=excluded.loc_no, cep=excluded.cep,
                loc_in_sit=excluded.loc_in_sit, loc_in_tipo=excluded.loc_in_tipo,
                loc_nu_sub=excluded.loc_nu_sub, loc_no_abrev=excluded.loc_no_abrev,
                mun_nu=excluded.mun_nu
            """,
            (loc_nu, ufe_sg, loc_no, cep, loc_in_sit, loc_in_tipo, loc_nu_sub, loc_no_abrev, mun_nu),
        )
        count += 1
    return count


def _load_bairros(conn: sqlite3.Connection, dne_path: Path) -> int:
    file_path = dne_path / "LOG_BAIRRO.TXT"
    if not file_path.exists():
        raise RuntimeError(f"Arquivo não encontrado: {file_path}")

    rows = _read_file(file_path)
    count = 0
    for row in rows:
        if len(row) < 5:
            row.extend([""] * (5 - len(row)))
        bai_nu, ufe_sg, loc_nu, bai_no, bai_no_abrev = (
            row[0], row[1], row[2], row[3], row[4]
        )
        conn.execute(
            """
            INSERT INTO bairro (bai_nu, ufe_sg, loc_nu, bai_no, bai_no_abrev)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(bai_nu) DO UPDATE SET
                ufe_sg=excluded.ufe_sg, loc_nu=excluded.loc_nu,
                bai_no=excluded.bai_no, bai_no_abrev=excluded.bai_no_abrev
            """,
            (bai_nu, ufe_sg, loc_nu, bai_no, bai_no_abrev),
        )
        count += 1
    return count


def _load_logradouros(conn: sqlite3.Connection, dne_path: Path) -> int:
    pattern = str(dne_path / "LOG_LOGRADOURO_*.TXT")
    files = glob.glob(pattern)
    if not files:
        raise RuntimeError(
            f"Nenhum arquivo LOG_LOGRADOURO_*.TXT encontrado em '{dne_path}'. "
            "Verifique se DNE_PATH aponta para a pasta correta."
        )

    count = 0
    for file_path in files:
        rows = _read_file(Path(file_path))
        for row in rows:
            if len(row) < 11:
                row.extend([""] * (11 - len(row)))
            (log_nu, ufe_sg, loc_nu, bai_nu_ini, bai_nu_fim,
             log_no, log_complemento, cep, tlo_tx, log_sta_tlo, log_no_abrev) = (
                row[0], row[1], row[2], row[3] or None, row[4] or None,
                row[5], row[6], row[7], row[8], row[9], row[10]
            )
            if not cep:
                continue
            conn.execute(
                """
                INSERT INTO logradouro
                    (log_nu, ufe_sg, loc_nu, bai_nu_ini, bai_nu_fim, log_no,
                     log_complemento, cep, tlo_tx, log_sta_tlo, log_no_abrev)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(log_nu) DO UPDATE SET
                    ufe_sg=excluded.ufe_sg, loc_nu=excluded.loc_nu,
                    bai_nu_ini=excluded.bai_nu_ini, bai_nu_fim=excluded.bai_nu_fim,
                    log_no=excluded.log_no, log_complemento=excluded.log_complemento,
                    cep=excluded.cep, tlo_tx=excluded.tlo_tx,
                    log_sta_tlo=excluded.log_sta_tlo, log_no_abrev=excluded.log_no_abrev
                """,
                (log_nu, ufe_sg, loc_nu, bai_nu_ini, bai_nu_fim, log_no,
                 log_complemento, cep, tlo_tx, log_sta_tlo, log_no_abrev),
            )
            count += 1
    return count


def run_etl(db_path: str | None = None, dne_path: str | None = None) -> dict:
    """Executa o ETL completo: lê os arquivos eDNE e carrega no banco."""
    base_path = Path(dne_path) if dne_path else _get_dne_path()

    with db_connection(db_path) as conn:
        create_schema(conn)
        n_loc = _load_localidades(conn, base_path)
        n_bai = _load_bairros(conn, base_path)
        n_log = _load_logradouros(conn, base_path)

    return {
        "localidades": n_loc,
        "bairros": n_bai,
        "logradouros": n_log,
    }
