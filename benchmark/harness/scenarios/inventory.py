"""Cenário `inventory` (Gestão de Estoque): ETL de vendas car-sales + API REST + dashboard + Web
com login. Rubrica de 11 dimensões (soma 100). Aponta para o conteúdo em `benchmark/inventory/`."""

from __future__ import annotations

from benchmark.harness.config import REPO_ROOT
from benchmark.harness.scenarios.base import Scenario
from benchmark.inventory import checks as inv_checks

DIMENSIONS = [
    "inventory_logic",
    "auth",
    "dashboard",
    "api_rest",
    "ingestao",
    "persistence",
    "tests",
    "error_handling",
    "architecture",
    "production",
    "git",
]

WEIGHTS = {
    "inventory_logic": 16,
    "auth": 14,
    "dashboard": 14,
    "api_rest": 12,
    "ingestao": 10,
    "persistence": 10,
    "tests": 9,
    "error_handling": 6,
    "architecture": 5,
    "production": 2,
    "git": 2,
}

COMBINATION = {
    "inventory_logic": (0.6, 0.4),
    "auth": (0.6, 0.4),
    "dashboard": (0.6, 0.4),
    "api_rest": (0.6, 0.4),
    "ingestao": (0.7, 0.3),
    "persistence": (0.5, 0.5),
    "tests": (0.6, 0.4),
    "error_handling": (0.7, 0.3),
    "architecture": (0.0, 1.0),
    "production": (0.6, 0.4),
    "git": (0.7, 0.3),
}

DIM_LABELS = {
    "inventory_logic": "Lógica de Estoque",
    "auth": "Autenticação",
    "dashboard": "Dashboard",
    "api_rest": "API REST",
    "ingestao": "Ingestão",
    "persistence": "Persistência",
    "tests": "Testes",
    "error_handling": "Tratamento de Erros",
    "architecture": "Arquitetura",
    "production": "Produção",
    "git": "Git",
}

DIM_DESCRIPTIONS = {
    "inventory_logic": "regras de estoque: entradas/saídas (in/out) atualizam o saldo, estoque "
                       "nunca fica negativo (saída > saldo → 400), CRUD de produto "
                       "por (Company, Model)",
    "auth": "autenticação: senha em HASH (nunca texto plano), login válido/inválido (200/401), "
            "rotas de escrita protegidas por Bearer token, formulário de login na Web",
    "dashboard": "dashboard de métricas: revenue/cost/profit/units_sold/movements e agregações "
                 "by_company/by_region coerentes com o dataset importado",
    "api_rest": "API REST (FastAPI): GET/POST de produtos, POST de movimentações, "
                "GET /api/dashboard, execução via uvx/uv run",
    "ingestao": "ETL de ingestão do CSV de vendas (schema car-sales): upsert de produtos e uma "
                "movimentação OUT por venda, idempotente",
    "persistence": "modelagem do banco: schema, índices, uniqueness e carga idempotente",
    "tests": "suíte de testes (pytest) cobre import/auth/estoque/dashboard e passa",
    "error_handling": "tratamento de dataset ausente, payloads inválidos e regras de estoque "
                      "violadas, sem stack trace cru",
    "architecture": "arquitetura em camadas (db/etl/auth/inventory/api/web/cli), coesão e clareza",
    "production": "preparação para produção: README, lint (ruff), CI (lint+testes), "
                  "empacotamento uv/uvx",
    "git": "interação com Git/GitHub: commits significativos, tag semver e push",
}

_BASE = REPO_ROOT / "benchmark" / "inventory"

SCENARIO = Scenario(
    id="inventory",
    dimensions=list(DIMENSIONS),
    weights=dict(WEIGHTS),
    combination=dict(COMBINATION),
    dim_labels=DIM_LABELS,
    dim_descriptions=DIM_DESCRIPTIONS,
    brief_dir=_BASE / "brief",
    rubric_md=_BASE / "rubric" / "rubric.md",
    judge_prompt=_BASE / "rubric" / "judge_prompt.md",
    sample_app=_BASE / "sample_app",
    db_filename="inventory.db",
    dataset_env="DATASET_PATH",
    run_checks=inv_checks.run_checks,
    extra_env={"ADMIN_USER": "admin", "ADMIN_PASSWORD": "admin123"},
    results_subdir="inventory",
    leaderboard_marker="INVENTORY",
)
