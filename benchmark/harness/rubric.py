"""Definição canônica da rubrica em código (espelha benchmark/rubric/rubric.md)."""

from __future__ import annotations

from dataclasses import dataclass

# Chaves estáveis das 9 dimensões (mesmas chaves usadas pelo JSON do juiz).
DIMENSIONS = [
    "etl_parsing",
    "completeness",
    "interfaces",
    "persistence",
    "tests",
    "error_handling",
    "architecture",
    "production",
    "git",
]

# Peso de cada dimensão (soma = 100).
WEIGHTS = {
    "etl_parsing": 18,
    "completeness": 13,
    "interfaces": 14,
    "persistence": 11,
    "tests": 11,
    "error_handling": 9,
    "architecture": 8,
    "production": 8,
    "git": 8,
}

# Combinação objetivo × juízes por dimensão (peso_obj, peso_juiz). Soma = 1.0.
COMBINATION = {
    "etl_parsing": (0.7, 0.3),
    "completeness": (1.0, 0.0),
    "interfaces": (0.6, 0.4),
    "persistence": (0.5, 0.5),
    "tests": (0.6, 0.4),
    "error_handling": (0.7, 0.3),
    "architecture": (0.0, 1.0),
    "production": (0.6, 0.4),
    "git": (0.7, 0.3),
}

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
