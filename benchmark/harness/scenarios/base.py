"""Abstração de Cenário: encapsula tudo que muda entre desafios (rubrica, brief, checks, dataset).

O harness é parametrizado por um `Scenario`. O cenário ativo é `it_assets` (Gestão de Movimentação
de Ativos de TI, 3 fases com mudança de direção + perturbação). A abstração permite adicionar
cenários sem tocar o orquestrador.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Scenario:
    """Contrato comum de um cenário de benchmark.

    Campos de rubrica (dimensions/weights/combination) seguem o mesmo formato de `rubric.py`.
    `run_checks(app_dir, dataset_path, expected) -> dict` roda as checagens objetivas caixa-preta
    e devolve `{"checks": [...], "objective_by_dimension": {...}, "flags": {...}, ...}` (ver
    `benchmark/it_assets/checks.py::run_checks`).
    """

    id: str
    dimensions: list[str]
    weights: dict[str, int]
    combination: dict[str, tuple[float, float]]
    dim_labels: dict[str, str]
    dim_descriptions: dict[str, str]

    # caminhos de conteúdo
    brief_dir: Path           # challenge.md + phase1/2/3_prompt.md
    rubric_md: Path           # rubrica humana (vai no prompt do juiz, placeholder {{RUBRIC}})
    judge_prompt: Path        # template do prompt do juiz
    sample_app: Path          # app de referência usado pelo selftest

    # execução
    db_filename: str          # nome do banco gerado (ex.: "cep.db", "it_assets.db")
    dataset_env: str          # env var com o caminho do dataset (ex.: "DATASET_PATH")
    run_checks: Callable[[Path, Path, dict], dict]

    # sequência de fases: nomes de prompt (sem .md) em benchmark/<id>/brief/. O índice 0 é o build;
    # os demais continuam a mesma sessão do agente.
    phase_prompts: list[str] = field(
        default_factory=lambda: ["phase1_prompt", "phase2_prompt", "phase3_prompt"])
    # há fase de git? (gitsetup/gitcheck/push/dimensão git). Default False (cenários novos).
    has_git_phase: bool = False
    # hooks executados ANTES da fase de dado índice (ex.: {2: perturb_dataset} muta a base
    # copiada antes da Fase 3). Recebem o app_dir do candidato.
    pre_phase_hooks: dict[int, Callable[[Path], None]] = field(default_factory=dict)

    # env extra fornecida ao agente E aos checks (ex.: credenciais semente)
    extra_env: dict[str, str] = field(default_factory=dict)

    # layout de saída (aditivo: cep usa raiz, cenários novos usam subpasta)
    results_subdir: str = ""          # "" => results/<slug>; senão results/<subdir>/<slug>
    leaderboard_marker: str = ""      # "" => LEADERBOARD; senão LEADERBOARD-<marker>

    def __post_init__(self) -> None:
        assert sum(self.weights.values()) == 100, f"pesos do cenário {self.id} devem somar 100"
        assert set(self.weights) == set(self.dimensions) == set(self.combination), \
            f"dimensions/weights/combination do cenário {self.id} devem coincidir"

    def results_dir(self, base_results_dir: Path) -> Path:
        return base_results_dir / self.results_subdir if self.results_subdir else base_results_dir

    def run_dir(self, base_runs_dir: Path, slug: str) -> Path:
        """Diretório de execução do candidato (app/logs) — namespaced por cenário para não
        colidir com outros cenários do mesmo candidato (ex.: runs_dir/<subdir>/<slug>)."""
        base = base_runs_dir / self.results_subdir if self.results_subdir else base_runs_dir
        return base / slug

    def leaderboard_path(self, base_results_dir: Path) -> Path:
        name = "leaderboard.md"
        return self.results_dir(base_results_dir) / name

    @property
    def markers(self) -> tuple[str, str]:
        suffix = f"-{self.leaderboard_marker}" if self.leaderboard_marker else ""
        return (f"<!-- LEADERBOARD{suffix}:START -->", f"<!-- LEADERBOARD{suffix}:END -->")
