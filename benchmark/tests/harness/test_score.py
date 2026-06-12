"""Testes da combinação objetivo×juiz e modificadores."""

from __future__ import annotations

from benchmark.harness.config import load_config
from benchmark.harness.rubric import DIMENSIONS
from benchmark.harness.score import compute_score


def _cfg():
    return load_config()


def test_perfect_objective_and_judge():
    cfg = _cfg()
    obj = {d: 100 for d in DIMENSIONS}
    jud = {d: 100 for d in DIMENSIONS}
    out = compute_score(obj, jud, {"load_time_s": 5}, cfg)
    # 100 + bônus de performance, clampeado em 100
    assert out["final_score"] == 100
    assert out["tier"] == "A"


def test_architecture_uses_judge_only():
    cfg = _cfg()
    obj = {d: 0 for d in DIMENSIONS}
    jud = {d: 100 for d in DIMENSIONS}
    out = compute_score(obj, jud, {}, cfg)
    # arquitetura é 100% juiz -> nota 100
    assert out["dimensions"]["architecture"]["note"] == 100


def test_completeness_uses_objective_only():
    cfg = _cfg()
    obj = {d: 0 for d in DIMENSIONS}
    obj["completeness"] = 100
    jud = {d: 0 for d in DIMENSIONS}
    out = compute_score(obj, jud, {}, cfg)
    assert out["dimensions"]["completeness"]["note"] == 100


def test_modifiers_penalties():
    cfg = _cfg()
    obj = {d: 100 for d in DIMENSIONS}
    jud = {d: 100 for d in DIMENSIONS}
    out = compute_score(obj, jud, {"hallucinated_dependency": True, "no_boot": True}, cfg)
    # 100 - 10 - 5 = 85
    assert out["final_score"] == 85


def test_judge_missing_falls_back_to_objective():
    cfg = _cfg()
    obj = {d: 80 for d in DIMENSIONS}
    jud = {d: None for d in DIMENSIONS}  # nenhum juiz
    out = compute_score(obj, jud, {}, cfg)
    # arquitetura (0% obj) cai para fallback objetivo = 80
    assert out["dimensions"]["architecture"]["note"] == 80
    assert out["final_score"] > 0


def test_architecture_excluded_when_no_source():
    cfg = _cfg()
    # todas as dimensões 100 no objetivo, MENOS architecture (sem objetivo) e sem juiz
    obj = {d: 100 for d in DIMENSIONS if d != "architecture"}
    jud = {d: None for d in DIMENSIONS}
    out = compute_score(obj, jud, {}, cfg)
    # architecture é excluída e os pesos renormalizam -> demais 100 => score 100 (não penaliza)
    assert "architecture" in out["excluded_dimensions"]
    assert out["dimensions"]["architecture"]["counted"] is False
    assert out["final_score"] == 100
    assert out["scored_weight"] == 92  # 100 - peso(8) da architecture
