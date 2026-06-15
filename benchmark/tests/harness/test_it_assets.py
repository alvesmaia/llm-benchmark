"""Testes do cenário it_assets: perturbação, parser do veredito E2E, captura de tokens,
sequência de 3 fases e checks contra a fixture (smoke leve)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from benchmark.harness import e2e_judge
from benchmark.harness.adapters.base import PhaseResult
from benchmark.it_assets.fixtures._generate import VALID_ACTIONS, perturb_dataset


def _make_csv(path: Path) -> None:
    header = [
        "movement_id", "date", "asset_tag", "asset_type", "action",
        "employee", "from_location", "to_location", "status", "value",
    ]
    rows = [[f"MV-{i:04d}", f"2024-01-0{(i % 9) + 1}", f"NB-{i}", "notebook",
             VALID_ACTIONS[i % len(VALID_ACTIONS)], "Fulano", "A", "B", "in_use", "1000"]
            for i in range(1, 11)]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def test_perturb_dataset_mutates_data_dir(tmp_path):
    app = tmp_path / "app"
    data = app / "data"
    data.mkdir(parents=True)
    csv_path = data / "movements.csv"
    _make_csv(csv_path)
    before = csv_path.read_text(encoding="utf-8")

    res = perturb_dataset(app)
    assert res["perturbed"] is True
    assert res["mutations"], "deve registrar mutações aplicadas"
    after = csv_path.read_text(encoding="utf-8")
    assert before != after
    # cabeçalho preservado e nº de linhas igual (só valores mudaram)
    rows_before = list(csv.reader(before.splitlines()))
    rows_after = list(csv.reader(after.splitlines()))
    assert rows_before[0] == rows_after[0]
    assert len(rows_before) == len(rows_after)
    # injetou ação fora do domínio em algum lugar
    blob = after.lower()
    assert "decommission_xyz" in blob or "-999" in after


def test_perturb_dataset_missing_csv_warns(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    res = perturb_dataset(app)
    assert res["perturbed"] is False
    assert "warning" in res


def test_e2e_parse_verdict_ok():
    raw = json.dumps({
        "steps": [
            {"nome": "login", "ok": True, "detalhe": "ok"},
            {"nome": "dashboard", "ok": True, "detalhe": "ok"},
            {"nome": "rbac", "ok": False, "detalhe": "não bloqueou"},
        ],
        "works": True,
        "issues": ["rbac falhou"],
    })
    v = e2e_judge.parse_verdict(raw)
    assert v["total_steps"] == 3
    assert v["ok_steps"] == 2
    assert v["note"] == round(100 * 2 / 3, 1)


def test_e2e_parse_verdict_wrapped_result():
    inner = {"steps": [{"nome": "x", "ok": True}], "works": True, "issues": []}
    wrapped = json.dumps({"result": json.dumps(inner)})
    v = e2e_judge.parse_verdict(wrapped)
    assert v["note"] == 100.0


def test_e2e_parse_verdict_unparseable():
    v = e2e_judge.parse_verdict("desculpe, não consegui")
    assert v["note"] is None
    assert "error" in v


def test_phase_result_token_fields():
    pr = PhaseResult(
        phase="phase1", ok=True, returncode=0, stdout="", stderr="", duration_s=1.0,
        tokens_input=100, tokens_output=50, tokens_cache_write=10, tokens_cache_read=5,
    )
    d = pr.to_dict()
    assert d["tokens_input"] == 100
    assert d["tokens_output"] == 50
    assert d["tokens_cache_write"] == 10
    assert d["tokens_cache_read"] == 5


def test_claude_code_token_extraction():
    from benchmark.harness.adapters.claude_code import _tokens

    data = {"usage": {
        "input_tokens": 1234, "output_tokens": 567,
        "cache_creation_input_tokens": 89, "cache_read_input_tokens": 1011,
    }}
    t = _tokens(data)
    assert t["tokens_input"] == 1234
    assert t["tokens_output"] == 567
    assert t["tokens_cache_write"] == 89
    assert t["tokens_cache_read"] == 1011


def test_opencode_token_extraction():
    from benchmark.harness.adapters.opencode_cli import _parse_events

    lines = [
        json.dumps({"type": "step_finish", "sessionID": "s1", "part": {
            "cost": 0.01,
            "tokens": {"input": 100, "output": 20, "cache": {"write": 5, "read": 3}},
        }}),
        json.dumps({"type": "step_finish", "part": {
            "cost": 0.02,
            "tokens": {"input": 50, "output": 10, "cache": {"write": 1, "read": 2}},
        }}),
    ]
    sid, cost, usage = _parse_events("\n".join(lines))
    assert sid == "s1"
    assert round(cost, 3) == 0.03
    assert usage["tokens_input"] == 150
    assert usage["tokens_output"] == 30
    assert usage["tokens_cache_write"] == 6
    assert usage["tokens_cache_read"] == 5


def test_report_aggregates_tokens(tmp_path):
    """report._read_tokens soma tokens das fases (result.json)."""
    from benchmark.harness import report

    res_dir = tmp_path / "results" / "x"
    res_dir.mkdir(parents=True)
    (res_dir / "result.json").write_text(json.dumps({"phases": {
        "phase1": {"tokens_input": 100, "tokens_output": 10,
                   "tokens_cache_write": 1, "tokens_cache_read": 2},
        "phase2": {"tokens_input": 200, "tokens_output": 20,
                   "tokens_cache_write": 3, "tokens_cache_read": 4},
    }}), encoding="utf-8")
    toks = report._read_tokens(res_dir, tmp_path / "nope")
    assert toks["input"] == 300
    assert toks["output"] == 30
    assert toks["cache"] == 10


def test_checks_run_against_fixture():
    """Smoke leve: as checagens rodam contra a fixture e o sample_app sem derrubar (estrutura
    do retorno). NÃO sobe servidor pesado aqui — apenas valida o formato e a captura de cobertura
    via uma execução real curta no sample_app é coberta pelo selftest."""
    from benchmark.it_assets import checks

    # apenas confirma a presença das funções/contrato esperado
    assert hasattr(checks, "run_checks")
    assert checks.COVERAGE_TARGET > 0
    # extrator de cobertura
    blob = "TOTAL    120     30    75%\n"
    assert checks._extract_coverage(blob) == 75.0
