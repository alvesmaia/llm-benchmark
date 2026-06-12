"""Testes da infra de cenários e do default de thinking."""

from __future__ import annotations

from benchmark.harness.config import Candidate
from benchmark.harness.scenarios.registry import get_scenario


def test_default_scenario_is_cep():
    sc = get_scenario()
    assert sc.id == "cep_etl"
    assert sum(sc.weights.values()) == 100
    assert set(sc.weights) == set(sc.dimensions) == set(sc.combination)


def test_inventory_scenario():
    inv = get_scenario("inventory")
    assert inv.id == "inventory"
    assert sum(inv.weights.values()) == 100
    assert set(inv.weights) == set(inv.dimensions) == set(inv.combination)
    assert inv.results_subdir == "inventory"
    assert inv.markers == ("<!-- LEADERBOARD-INVENTORY:START -->",
                           "<!-- LEADERBOARD-INVENTORY:END -->")
    # os 4 diferenciadores carregam mais peso que as dimensões de infra
    assert min(inv.weights[d] for d in ("inventory_logic", "auth", "dashboard", "api_rest")) \
        >= max(inv.weights[d] for d in ("production", "git"))


def test_scenario_namespacing(tmp_path):
    cep = get_scenario("cep_etl")
    inv = get_scenario("inventory")
    # cep usa a raiz; inventory usa subpasta — não colidem para o mesmo slug
    assert cep.run_dir(tmp_path, "x") != inv.run_dir(tmp_path, "x")
    assert inv.run_dir(tmp_path, "x").parts[-2] == "inventory"


def test_thinking_default_medium():
    c = Candidate(agent="a", model="m", model_slug="s")
    assert c.thinking == "medium"
    assert c.runs_scenario("cep_etl") is True
    assert c.runs_scenario("inventory") is False  # default: só cep
