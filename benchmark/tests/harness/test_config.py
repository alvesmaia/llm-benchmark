"""Testes do carregamento de config e helpers."""

from __future__ import annotations

from benchmark.harness.config import load_config, slugify


def test_load_config():
    cfg = load_config()
    assert cfg.dataset_for("it_assets").exists(), "fixture it_assets deve existir"
    assert cfg.expected_for("it_assets").exists()
    assert len(cfg.candidates) >= 1
    assert len(cfg.judges) == 2
    assert (cfg.raw.get("e2e_judge") or {}).get("model") == "sonnet"


def test_candidate_slug():
    cfg = load_config()
    slugs = [c.slug for c in cfg.candidates]
    # ranking é por harness+modelo: claude e copilot são distintos
    assert "claude_code-opus-4-8" in slugs
    assert "claude_code-sonnet" in slugs
    assert any(s.startswith("copilot_cli-") for s in slugs)
    assert len(slugs) == len(set(slugs)), "slugs devem ser únicos"


def test_slugify():
    assert slugify("GPT 5.1 Codex") == "gpt-5-1-codex"
