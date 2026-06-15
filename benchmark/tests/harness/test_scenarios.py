"""Testes da infra de cenários (it_assets), fases e default de thinking."""

from __future__ import annotations

from benchmark.harness.config import Candidate
from benchmark.harness.scenarios.registry import KNOWN, get_scenario


def test_default_scenario_is_it_assets():
    sc = get_scenario()
    assert sc.id == "it_assets"
    assert KNOWN == ["it_assets"]
    assert sum(sc.weights.values()) == 100
    assert set(sc.weights) == set(sc.dimensions) == set(sc.combination)
    assert len(sc.dimensions) == 12


def test_it_assets_phases_and_hooks():
    sc = get_scenario("it_assets")
    # 3 fases, sem git, hook de perturbação antes da Fase 3 (índice 2)
    assert sc.phase_prompts == ["phase1_prompt", "phase2_prompt", "phase3_prompt"]
    assert sc.has_git_phase is False
    assert 2 in sc.pre_phase_hooks and callable(sc.pre_phase_hooks[2])
    assert sc.db_filename == "it_assets.db"
    assert sc.dataset_env == "DATASET_PATH"
    # cenário único usa a raiz dos results (sem subpasta) e marcadores padrão
    assert sc.results_subdir == ""
    assert sc.markers == ("<!-- LEADERBOARD:START -->", "<!-- LEADERBOARD:END -->")


def test_differentiators_have_weight():
    sc = get_scenario("it_assets")
    # diferenciadores (refactor/resiliencia/e2e) carregam mais peso que infra (production)
    assert min(sc.weights[d] for d in ("refactor", "resiliencia", "e2e")) > sc.weights["production"]


def test_unknown_scenario_raises():
    import pytest

    with pytest.raises(ValueError):
        get_scenario("cep_etl")


def test_thinking_default_medium():
    c = Candidate(agent="a", model="m", model_slug="s")
    assert c.thinking == "medium"
    assert c.runs_scenario("it_assets") is True
    assert c.runs_scenario("inventory") is False  # cenário inexistente
