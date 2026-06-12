"""Registro de cenários. `get_scenario(id)` resolve o cenário (default `cep_etl`)."""

from __future__ import annotations

from benchmark.harness.scenarios.base import Scenario

DEFAULT_SCENARIO = "cep_etl"
KNOWN = ["cep_etl", "inventory"]


def get_scenario(scenario_id: str | None = None) -> Scenario:
    sid = scenario_id or DEFAULT_SCENARIO
    if sid == "cep_etl":
        from benchmark.harness.scenarios import cep_etl
        return cep_etl.SCENARIO
    if sid == "inventory":
        from benchmark.harness.scenarios import inventory
        return inventory.SCENARIO
    raise ValueError(f"cenário desconhecido: {sid} (conhecidos: {KNOWN})")
