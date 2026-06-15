"""Cenário `it_assets` (Gestão de Movimentação de Ativos de TI) — único cenário do benchmark.

3 fases com mudança de direção + perturbação dirigida:
  1. Dashboard Streamlit sobre a base de movimentação de ativos de TI.
  2. Refatoração (pivô) para FastAPI + SQLite + Jinja2 + JWT + RBAC.
  3. O harness muta a base copiada em `data/` e o modelo corrige (testes voltam a passar).

Sem fase de git. Pontua o estado FINAL (pós-Fase 3). Rubrica de 12 dimensões (soma 100).
"""

from __future__ import annotations

from benchmark.harness.config import REPO_ROOT
from benchmark.harness.scenarios.base import Scenario
from benchmark.it_assets import checks as it_checks
from benchmark.it_assets.fixtures._generate import perturb_dataset

DIMENSIONS = [
    "refactor",
    "resiliencia",
    "e2e",
    "auth_jwt",
    "rbac",
    "dashboard",
    "persistence",
    "tests",
    "api_web",
    "execucao_uvx",
    "ingestao",
    "production",
]

WEIGHTS = {
    "refactor": 13,
    "resiliencia": 12,
    "e2e": 11,
    "auth_jwt": 10,
    "rbac": 10,
    "dashboard": 9,
    "persistence": 8,
    "tests": 8,
    "api_web": 7,
    "execucao_uvx": 6,
    "ingestao": 4,
    "production": 2,
}

# (peso_obj, peso_juiz) por dimensão. Soma = 1.0.
COMBINATION = {
    "refactor": (0.0, 1.0),       # qualidade arquitetural pós-pivô: juiz
    "resiliencia": (0.6, 0.4),    # recuperação objetiva + leitura do juiz
    "e2e": (1.0, 0.0),            # veredito Playwright/Sonnet (objetivo)
    "auth_jwt": (0.7, 0.3),
    "rbac": (0.7, 0.3),
    "dashboard": (0.3, 0.7),
    "persistence": (0.5, 0.5),
    "tests": (0.7, 0.3),          # cobertura medida + relevância (juiz)
    "api_web": (0.6, 0.4),
    "execucao_uvx": (0.7, 0.3),
    "ingestao": (0.6, 0.4),
    "production": (0.6, 0.4),
}

DIM_LABELS = {
    "refactor": "Refatoração",
    "resiliencia": "Resiliência",
    "e2e": "E2E",
    "auth_jwt": "Auth JWT",
    "rbac": "RBAC",
    "dashboard": "Dashboard",
    "persistence": "Persistência",
    "tests": "Testes",
    "api_web": "API/Web",
    "execucao_uvx": "Execução uvx",
    "ingestao": "Ingestão",
    "production": "Produção",
}

DIM_DESCRIPTIONS = {
    "refactor": "qualidade da virada Streamlit→FastAPI/SQLite/Jinja2/JWT/RBAC: reaproveitamento "
                "do código do dashboard e organização em camadas coesas",
    "resiliencia": "recuperação após a perturbação dirigida da base (Fase 3): testes e boot voltam "
                   "a passar sobre os dados mutados; ingestão/validação robustas",
    "e2e": "veredito de um agente Playwright/Sonnet que usa a app como usuário: login, dashboard "
           "e bloqueio de ação restrita (% de passos OK)",
    "auth_jwt": "JWT: login válido→token / inválido→401; rotas protegidas exigem Bearer (401 sem)",
    "rbac": "RBAC: ≥2 papéis; ação de escrita/admin negada com 403 ao papel sem permissão",
    "dashboard": "métricas úteis de movimentação (por status/local/colaborador/tempo) coerentes",
    "persistence": "SQLite: schema/índices e carga a partir da base",
    "tests": "testes pytest com cobertura medida (alvo OCULTO); devem passar",
    "api_web": "endpoints REST + telas Jinja2 que respondem HTML",
    "execucao_uvx": "um único comando `uvx` sobe a app lendo o `.env` versionado",
    "ingestao": "leitura/parse da base de movimentações de ativos de TI",
    "production": "README com o comando único, lint (ruff), empacotamento uv/uvx",
}

_BASE = REPO_ROOT / "benchmark" / "it_assets"

SCENARIO = Scenario(
    id="it_assets",
    dimensions=list(DIMENSIONS),
    weights=dict(WEIGHTS),
    combination=dict(COMBINATION),
    dim_labels=DIM_LABELS,
    dim_descriptions=DIM_DESCRIPTIONS,
    brief_dir=_BASE / "brief",
    rubric_md=_BASE / "rubric" / "rubric.md",
    judge_prompt=_BASE / "rubric" / "judge_prompt.md",
    sample_app=_BASE / "sample_app",
    db_filename="it_assets.db",
    dataset_env="DATASET_PATH",
    run_checks=it_checks.run_checks,
    phase_prompts=["phase1_prompt", "phase2_prompt", "phase3_prompt"],
    has_git_phase=False,
    pre_phase_hooks={2: perturb_dataset},
    extra_env={
        "ADMIN_USER": "admin", "ADMIN_PASSWORD": "admin123",
        "VIEWER_USER": "viewer", "VIEWER_PASSWORD": "viewer123",
    },
    results_subdir="",
    leaderboard_marker="",
)
