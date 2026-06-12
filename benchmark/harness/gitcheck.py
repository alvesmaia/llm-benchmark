"""Checagens objetivas de git/GitHub para a dimensão 9 da rubrica."""

from __future__ import annotations

import re
from pathlib import Path

from benchmark.harness.adapters.base import run_command
from benchmark.harness.config import GitConfig

SEMVER_RE = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?:\s+.+",
    re.IGNORECASE,
)
TRIVIAL_MESSAGES = {"wip", "update", "fix", "changes", "stuff", "asdf", "commit", ".", "test"}


def _git(args: list[str], cwd: Path) -> tuple[int, str]:
    rc, out, _err, _ = run_command(["git", *args], cwd=cwd, timeout=120)
    return rc, out.strip()


def _commit_messages(app_dir: Path) -> list[str]:
    rc, out = _git(["log", "--pretty=%s"], app_dir)
    if rc != 0 or not out:
        return []
    return [line for line in out.splitlines() if line.strip()]


def _is_meaningful(msg: str) -> bool:
    m = msg.strip().lower()
    if m in TRIVIAL_MESSAGES:
        return False
    # mensagens muito curtas (1 palavra, < 12 chars) tendem a ser triviais
    return not (len(m) < 12 and len(m.split()) <= 1)


def check_git(app_dir: Path, slug: str, git: GitConfig) -> dict:
    """Retorna sub-notas (0-100) e detalhes para a dimensão git."""
    if not (app_dir / ".git").exists():
        return {"note": 0, "detail": "sem repositório git", "sub": {}}

    messages = _commit_messages(app_dir)
    n = len(messages)

    # commit_count: >=2 -> 100, 1 -> 50, 0 -> 0
    commit_count_note = 100 if n >= 2 else (50 if n == 1 else 0)

    # msg_quality: proporção de mensagens significativas; bônus por Conventional Commits
    if n:
        meaningful = sum(1 for m in messages if _is_meaningful(m))
        conventional = sum(1 for m in messages if CONVENTIONAL_RE.match(m))
        base = 100 * meaningful / n
        bonus = 10 * conventional / n
        msg_quality_note = min(100, base + bonus)
    else:
        msg_quality_note = 0

    # semver_tag: alguma tag no formato semver?
    rc, tag_out = _git(["tag", "--list"], app_dir)
    tags = [t for t in tag_out.splitlines() if t.strip()] if rc == 0 else []
    semver_tags = [t for t in tags if SEMVER_RE.match(t.strip())]
    semver_note = 100 if semver_tags else 0

    sub = {
        "commit_count": commit_count_note,
        "msg_quality": round(msg_quality_note, 1),
        "semver_tag": semver_note,
    }

    # push_ok: só conta quando push está habilitado
    push_na = True
    if git.push_enabled and git.github_remote:
        push_na = False
        branch = f"{git.branch_prefix}{slug}"
        rc, _o = _git(["ls-remote", "--heads", "origin", branch], app_dir)
        push_ok_note = 100 if (rc == 0 and _o.strip()) else 0
        sub["push_ok"] = push_ok_note

    # Nota agregada: média das sub-notas presentes.
    note = round(sum(sub.values()) / len(sub), 1) if sub else 0

    return {
        "note": note,
        "sub": sub,
        "n_commits": n,
        "tags": tags,
        "semver_tags": semver_tags,
        "push_evaluated": not push_na,
    }
