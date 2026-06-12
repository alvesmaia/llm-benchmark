"""Carregamento e modelagem da configuração do harness (config.yaml)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Raiz do repositório (3 níveis acima deste arquivo: benchmark/harness/config.py).
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "benchmark" / "harness" / "config.yaml"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-")


@dataclass
class Candidate:
    agent: str
    model: str
    model_slug: str
    context: str | None = None  # janela de contexto declarada (ex.: "1M", "200K")
    display: str | None = None  # nome limpo de exibição (ex.: "Opus 4.8")

    @property
    def slug(self) -> str:
        return f"{self.agent}-{self.model_slug}"


@dataclass
class Judge:
    id: str
    agent: str
    model: str


@dataclass
class GitConfig:
    github_remote: str = ""
    push_enabled: bool = False
    branch_prefix: str = "run/"
    tag_namespace: bool = True


@dataclass
class Config:
    dne_path: Path
    expected_queries: Path
    runs_dir: Path
    results_dir: Path
    git: GitConfig
    modifiers: dict
    divergence_flag_threshold: float
    judges: list[Judge]
    candidates: list[Candidate]
    raw: dict = field(default_factory=dict)

    def candidate_by_slug(self, slug: str) -> Candidate | None:
        return next((c for c in self.candidates if c.slug == slug), None)


def _abspath(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (REPO_ROOT / p)


def load_config(path: str | Path | None = None) -> Config:
    cfg_path = Path(path) if path else DEFAULT_CONFIG
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    git = GitConfig(**(data.get("git") or {}))
    judges = [Judge(**j) for j in data.get("judges", [])]
    candidates = [Candidate(**c) for c in data.get("candidates", [])]

    return Config(
        dne_path=_abspath(data["dne_path"]),
        expected_queries=_abspath(data["expected_queries"]),
        runs_dir=_abspath(data.get("runs_dir", "runs")),
        results_dir=_abspath(data.get("results_dir", "results")),
        git=git,
        modifiers=data.get("modifiers", {}),
        divergence_flag_threshold=float(data.get("divergence_flag_threshold", 25)),
        judges=judges,
        candidates=candidates,
        raw=data,
    )
