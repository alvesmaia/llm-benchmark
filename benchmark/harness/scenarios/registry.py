"""Registro de cenários. `get_scenario(id)` resolve o cenário (default `it_assets`)."""

from __future__ import annotations

from benchmark.harness.scenarios.base import Scenario

DEFAULT_SCENARIO = "it_assets"
KNOWN = ["it_assets"]


def get_scenario(scenario_id: str | None = None) -> Scenario:
    sid = scenario_id or DEFAULT_SCENARIO
    if sid == "it_assets":
        from benchmark.harness.scenarios import it_assets
        return it_assets.SCENARIO
    raise ValueError(f"cenário desconhecido: {sid} (conhecidos: {KNOWN})")
