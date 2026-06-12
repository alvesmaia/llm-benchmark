"""Testes do export ZIP (app + prompt do juiz + resultados) para reavaliação externa."""

from __future__ import annotations

import zipfile

from benchmark.harness import export as export_mod
from benchmark.harness.config import load_config
from benchmark.harness.scenarios.registry import get_scenario


def test_export_candidate_zip(tmp_path):
    cfg = load_config()
    cfg.runs_dir = tmp_path / "runs"
    cfg.results_dir = tmp_path / "results"
    sc = get_scenario("cep_etl")
    slug = "fake-cand"

    run_dir = sc.run_dir(cfg.runs_dir, slug)
    app = run_dir / "app"
    logs = run_dir / "logs"
    app.mkdir(parents=True)
    logs.mkdir(parents=True)
    (app / "main.py").write_text("print('hi')", encoding="utf-8")
    venv = app / ".venv"
    venv.mkdir()
    (venv / "ignore.txt").write_text("skip", encoding="utf-8")
    (logs / "judge_prompt.md").write_text("PROMPT DO JUIZ", encoding="utf-8")
    res = sc.results_dir(cfg.results_dir) / slug
    res.mkdir(parents=True)
    (res / "scores.json").write_text("{}", encoding="utf-8")

    out = export_mod.export_candidate(cfg, slug, sc, out_dir=tmp_path / "exp")
    assert out.exists()
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    assert "app/main.py" in names
    assert "judge_prompt.md" in names           # prompt na raiz do ZIP (acesso direto)
    assert "logs/judge_prompt.md" in names
    assert "results/scores.json" in names
    assert not any(".venv" in n for n in names)  # diretórios pesados são pulados
