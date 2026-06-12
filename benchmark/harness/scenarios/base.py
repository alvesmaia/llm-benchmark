"""Abstração de Cenário: encapsula tudo que muda entre desafios (rubrica, brief, checks, dataset).

O harness é parametrizado por um `Scenario`. O default histórico é `cep_etl` (desafio ETL CEP),
preservando 100% o comportamento atual. Cenários novos (ex.: `inventory`) vivem em paralelo.
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
    e devolve `{"checks": [...], "objective_by_dimension": {...}, "flags": {...}, ...}` (mesmo
    formato de `checks.run_all_checks`).
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
    db_filename: str          # nome do banco gerado (ex.: "cep.db", "inventory.db")
    dataset_env: str          # env var com o caminho do dataset (ex.: "DNE_PATH", "DATASET_PATH")
    run_checks: Callable[[Path, Path, dict], dict]

    # env extra fornecida ao agente E aos checks (ex.: credenciais semente do inventory)
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
        colidir com outros cenários do mesmo candidato (ex.: runs_dir/inventory/<slug>)."""
        base = base_runs_dir / self.results_subdir if self.results_subdir else base_runs_dir
        return base / slug

    def leaderboard_path(self, base_results_dir: Path) -> Path:
        name = "leaderboard.md"
        return self.results_dir(base_results_dir) / name

    @property
    def markers(self) -> tuple[str, str]:
        suffix = f"-{self.leaderboard_marker}" if self.leaderboard_marker else ""
        return (f"<!-- LEADERBOARD{suffix}:START -->", f"<!-- LEADERBOARD{suffix}:END -->")
