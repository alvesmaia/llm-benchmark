"""Testes da definição da rubrica."""

from __future__ import annotations

from benchmark.harness.rubric import COMBINATION, DIMENSIONS, WEIGHTS, tier_for


def test_weights_sum_100():
    assert sum(WEIGHTS.values()) == 100


def test_dimensions_consistent():
    assert set(WEIGHTS) == set(DIMENSIONS) == set(COMBINATION)


def test_combination_sums_to_one():
    for dim, (a, b) in COMBINATION.items():
        assert abs((a + b) - 1.0) < 1e-9, dim


def test_tiers():
    assert tier_for(95).name == "A"
    assert tier_for(80).name == "A"
    assert tier_for(79).name == "B"
    assert tier_for(60).name == "B"
    assert tier_for(59).name == "C"
    assert tier_for(40).name == "C"
    assert tier_for(39).name == "D"
    assert tier_for(0).name == "D"
