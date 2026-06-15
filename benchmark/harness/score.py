"""Combina notas objetivas + média do painel de juízes em score final 0-100 e tier."""

from __future__ import annotations

from benchmark.harness.config import Config
from benchmark.harness.rubric import tier_for


def _dimension_note(dim: str, objective: float | None,
                    judge: float | None, combination: dict) -> tuple[float, bool, str]:
    """Combina objetivo×juiz para uma dimensão. Retorna (nota, tem_fonte, origem).

    tem_fonte=False quando não há nenhuma fonte (objetivo nem juiz) — nesse caso a dimensão é
    excluída do score e os pesos são renormalizados, em vez de penalizar com 0.
    """
    w_obj, w_judge = combination[dim]
    has_obj = objective is not None and w_obj > 0
    has_judge = judge is not None and w_judge > 0

    if has_obj and has_judge:
        return w_obj * objective + w_judge * judge, True, "obj+juiz"
    if has_obj:
        return float(objective), True, "só obj (sem juiz)"
    if has_judge:
        return float(judge), True, "só juiz (sem obj)"
    # nenhuma fonte ponderada: usa o que existir (peso 0), senão marca sem-fonte
    if objective is not None:
        return float(objective), True, "obj (fallback)"
    if judge is not None:
        return float(judge), True, "juiz (fallback)"
    return 0.0, False, "sem fonte (excluída do score)"


def compute_score(objective_by_dimension: dict, judge_avg: dict, flags: dict,
                  cfg: Config, scenario=None) -> dict:
    from benchmark.harness.scenarios.registry import get_scenario
    sc = scenario or get_scenario()
    dimensions, weights, combination = sc.dimensions, sc.weights, sc.combination

    mods_cfg = cfg.modifiers or {}
    dim_notes = {}
    weighted_acc = 0.0
    scored_weight = 0
    excluded = []
    for dim in dimensions:
        obj = objective_by_dimension.get(dim)
        jud = judge_avg.get(dim)
        note, has_source, source = _dimension_note(dim, obj, jud, combination)
        note = max(0.0, min(100.0, note))
        dim_notes[dim] = {"note": round(note, 1), "objective": obj, "judge": jud,
                          "source": source, "counted": has_source}
        if has_source:
            weighted_acc += weights[dim] * note / 100.0
            scored_weight += weights[dim]
        else:
            excluded.append(dim)

    # renormaliza para 0-100 sobre as dimensões com fonte (não penaliza dimensão sem juiz)
    weighted_sum = (weighted_acc * 100.0 / scored_weight) if scored_weight else 0.0

    # modificadores
    applied = []
    total = weighted_sum

    if flags.get("hallucinated_dependency"):
        v = mods_cfg.get("hallucinated_dependency", -10)
        total += v
        applied.append({"id": "hallucinated_dependency", "value": v})

    if flags.get("no_boot"):
        v = mods_cfg.get("no_boot", -5)
        total += v
        applied.append({"id": "no_boot", "value": v})

    load_time = flags.get("load_time_s")
    threshold = mods_cfg.get("load_time_threshold_seconds", 60)
    # só dá bônus se a carga de fato ocorreu (load_time conhecido e > 0) e foi rápida
    if load_time is not None and 0 < load_time < threshold and not flags.get("no_boot"):
        v = mods_cfg.get("load_performance_bonus", 3)
        total += v
        applied.append({"id": "load_performance_bonus", "value": v})

    final = max(0.0, min(100.0, round(total, 1)))
    tier = tier_for(final)

    return {
        "dimensions": dim_notes,
        "weighted_subtotal": round(weighted_sum, 1),
        "excluded_dimensions": excluded,
        "scored_weight": scored_weight,
        "modifiers_applied": applied,
        "final_score": final,
        "tier": tier.name,
        "tier_note": tier.note,
    }
