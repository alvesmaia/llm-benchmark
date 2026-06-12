"""Cenário `cep_etl`: o desafio ETL CEP Correios (default histórico). Aponta para os arquivos,
rubrica e checks já existentes — não altera nada do comportamento atual."""

from __future__ import annotations

from benchmark.harness import checks as checks_mod
from benchmark.harness.config import REPO_ROOT
from benchmark.harness.rubric import COMBINATION, DIMENSIONS, WEIGHTS
from benchmark.harness.scenarios.base import Scenario

DIM_LABELS = {
    "etl_parsing": "ETL",
    "completeness": "Completude",
    "interfaces": "Interfaces",
    "persistence": "Persistência",
    "tests": "Testes",
    "error_handling": "Tratamento de Erros",
    "architecture": "Arquitetura",
    "production": "Produção",
    "git": "Git",
}

DIM_DESCRIPTIONS = {
    "etl_parsing": "correção do ETL/parsing da base DNE (encoding Latin-1, separador `@`, "
                   "mapeamento de campos, fallback de CEP de localidade)",
    "completeness": "completude dos entregáveis obrigatórios (ETL, consulta, CLI, API, Web, "
                    "testes, README, lint/CI)",
    "interfaces": "as três interfaces de consulta (CLI, API REST e Web) funcionam, aceitam 1+ "
                  "CEPs, e o projeto roda via `uv run`/`uvx`",
    "persistence": "modelagem do banco: schema, índice por CEP e carga idempotente",
    "tests": "suíte de testes (pytest) cobre ETL/consulta/erros e passa",
    "error_handling": "tratamento de CEP inválido, CEP não encontrado e base DNE ausente",
    "architecture": "arquitetura e organização do código (modularidade, separação de camadas)",
    "production": "preparação para produção (CI, README, lint/ruff, empacotamento)",
    "git": "interação com Git/GitHub: commits significativos, tag semver e push",
}

_BRIEF = REPO_ROOT / "benchmark" / "brief"
_RUBRIC = REPO_ROOT / "benchmark" / "rubric"

SCENARIO = Scenario(
    id="cep_etl",
    dimensions=list(DIMENSIONS),
    weights=dict(WEIGHTS),
    combination=dict(COMBINATION),
    dim_labels=DIM_LABELS,
    dim_descriptions=DIM_DESCRIPTIONS,
    brief_dir=_BRIEF,
    rubric_md=_RUBRIC / "rubric.md",
    judge_prompt=_RUBRIC / "judge_prompt.md",
    sample_app=REPO_ROOT / "benchmark" / "tests" / "sample_app",
    db_filename="cep.db",
    dataset_env="DNE_PATH",
    run_checks=checks_mod.run_all_checks,
    results_subdir="",
    leaderboard_marker="",
)
