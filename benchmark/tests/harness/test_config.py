"""Testes do carregamento de config e helpers."""

from __future__ import annotations

from benchmark.harness.config import load_config, slugify


def test_load_config():
    cfg = load_config()
    assert cfg.dne_path.exists(), "fixture DNE deve existir"
    assert cfg.expected_queries.exists()
    assert len(cfg.candidates) >= 1
    assert len(cfg.judges) == 2


def test_candidate_slug():
    cfg = load_config()
    slugs = [c.slug for c in cfg.candidates]
    # ranking é por harness+modelo: claude e copilot com opus são distintos
    assert "claude_code-opus" in slugs
    assert any(s.startswith("copilot_cli-") for s in slugs)
    assert len(slugs) == len(set(slugs)), "slugs devem ser únicos"


def test_slugify():
    assert slugify("GPT 5.1 Codex") == "gpt-5-1-codex"
