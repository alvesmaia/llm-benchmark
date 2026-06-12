"""Combina notas objetivas + média do painel de juízes em score final 0-100 e tier."""

from __future__ import annotations

from benchmark.harness.config import Config
from benchmark.harness.rubric import COMBINATION, DIMENSIONS, WEIGHTS, tier_for


def _dimension_note(dim: str, objective: float | None, judge: float | None) -> tuple[float, str]:
    """Combina objetivo×juiz para uma dimensão, com fallback quando uma fonte falta."""
    w_obj, w_judge = COMBINATION[dim]
    has_obj = objective is not None and w_obj > 0
    has_judge = judge is not None and w_judge > 0

    if has_obj and has_judge:
        return w_obj * objective + w_judge * judge, "obj+juiz"
    if has_obj:
        return float(objective), "só obj (sem juiz)"
    if has_judge:
        return float(judge), "só juiz (sem obj)"
    # nenhuma fonte: se há objetivo mesmo com peso 0, usa; senão 0
    if objective is not None:
        return float(objective), "obj (fallback)"
    if judge is not None:
        return float(judge), "juiz (fallback)"
    return 0.0, "sem fonte"


def compute_score(objective_by_dimension: dict, judge_avg: dict, flags: dict,
                  cfg: Config) -> dict:
    mods_cfg = cfg.modifiers or {}
    dim_notes = {}
    weighted_sum = 0.0
    for dim in DIMENSIONS:
        obj = objective_by_dimension.get(dim)
        jud = judge_avg.get(dim)
        note, source = _dimension_note(dim, obj, jud)
        note = max(0.0, min(100.0, note))
        dim_notes[dim] = {"note": round(note, 1), "objective": obj, "judge": jud, "source": source}
        weighted_sum += WEIGHTS[dim] * note / 100.0

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
        "modifiers_applied": applied,
        "final_score": final,
        "tier": tier.name,
        "tier_note": tier.note,
    }
