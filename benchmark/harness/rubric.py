"""Tiers do score + reexport das dimensões/pesos canônicos do cenário ativo (it_assets).

Historicamente este módulo guardava a rubrica do CEP. Com o cenário único `it_assets`, a fonte
canônica de dimensões/pesos/combinação é `scenarios/it_assets.py`; aqui apenas reexportamos para
compatibilidade e mantemos `tier_for`/`TIERS` (independentes de cenário).
"""

from __future__ import annotations

from dataclasses import dataclass

from benchmark.harness.scenarios.it_assets import COMBINATION, DIMENSIONS, WEIGHTS

assert sum(WEIGHTS.values()) == 100, "Os pesos da rubrica devem somar 100"
assert set(WEIGHTS) == set(DIMENSIONS) == set(COMBINATION)


@dataclass
class Tier:
    name: str
    low: int
    high: int
    note: str


TIERS = [
    Tier("A", 80, 100, "Pronto para produção (patch < 30 min)"),
    Tier("B", 60, 79, "1–2 h de ajustes; arquitetura sólida com lacunas menores"),
    Tier("C", 40, 59, "Retrabalho grande"),
    Tier("D", 0, 39, "Quebrado / incompleto"),
]


def tier_for(score: float) -> Tier:
    s = max(0, min(100, round(score)))
    for t in TIERS:
        if t.low <= s <= t.high:
            return t
    return TIERS[-1]
