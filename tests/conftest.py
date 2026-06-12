"""Fixtures compartilhadas para os testes."""


import pytest

from cep_etl.etl import run_etl


@pytest.fixture
def dne_path(tmp_path):
    """Cria uma pasta temporária com arquivos eDNE de amostra."""
    loc = tmp_path / "LOG_LOCALIDADE.TXT"
    loc.write_text(
        "1@SP@São Paulo@@0@0@@S.Paulo@3550308\n"
        "2@RJ@Rio de Janeiro@@0@0@@R.Janeiro@3304557\n"
        "3@SP@Campinas@@0@0@@Campinas@3509502\n"
        "4@MG@Borda da Mata@37564000@1@0@@Borda Mata@3108503\n",
        encoding="latin-1",
    )

    bai = tmp_path / "LOG_BAIRRO.TXT"
    bai.write_text(
        "1@SP@1@Sé@Sé\n"
        "2@SP@1@Bela Vista@B.Vista\n"
        "3@RJ@2@Centro@Centro\n"
        "4@SP@3@Centro@Centro\n",
        encoding="latin-1",
    )

    log_sp = tmp_path / "LOG_LOGRADOURO_SP.TXT"
    log_sp.write_text(
        "1@SP@1@1@@Praça da Sé@lado ímpar@01001000@Praça@S@Pç da Sé\n"
        "2@SP@1@2@@Avenida Paulista@@01310100@Avenida@S@Av Paulista\n"
        "3@SP@3@4@@Avenida Francisco Glicério@@13012100@Avenida@S@Av Fco Glicério\n",
        encoding="latin-1",
    )

    log_rj = tmp_path / "LOG_LOGRADOURO_RJ.TXT"
    log_rj.write_text(
        "10@RJ@2@3@@Avenida Rio Branco@@20040002@Avenida@S@Av Rio Branco\n",
        encoding="latin-1",
    )

    return str(tmp_path)


@pytest.fixture
def db_path(tmp_path):
    """Retorna um caminho temporário para o banco SQLite."""
    return str(tmp_path / "test_cep.db")


@pytest.fixture
def loaded_db(dne_path, db_path):
    """Banco de dados já carregado com os dados de amostra."""
    run_etl(db_path=db_path, dne_path=dne_path)
    return db_path
