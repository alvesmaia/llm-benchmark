"""Testes das checagens de git (dimensão 9)."""

from __future__ import annotations

from benchmark.harness.adapters.base import run_command
from benchmark.harness.config import GitConfig
from benchmark.harness.gitcheck import check_git


def _init_repo(path):
    run_command(["git", "init", "-q"], cwd=path, timeout=60)
    run_command(["git", "checkout", "-q", "-B", "main"], cwd=path, timeout=60)
    run_command(["git", "config", "user.name", "t"], cwd=path, timeout=60)
    run_command(["git", "config", "user.email", "t@t.local"], cwd=path, timeout=60)


def _commit(path, name, msg):
    (path / name).write_text("x", encoding="utf-8")
    run_command(["git", "add", "-A"], cwd=path, timeout=60)
    run_command(["git", "commit", "-q", "-m", msg], cwd=path, timeout=60)


def test_good_history(tmp_path):
    _init_repo(tmp_path)
    _commit(tmp_path, "a.py", "feat: implementa ETL da base CEP")
    _commit(tmp_path, "b.py", "test: adiciona testes de consulta")
    run_command(["git", "tag", "v0.1.0"], cwd=tmp_path, timeout=60)

    res = check_git(tmp_path, "x-y", GitConfig())
    assert res["sub"]["commit_count"] == 100
    assert res["sub"]["semver_tag"] == 100
    assert res["sub"]["msg_quality"] >= 100  # conventional commits dão o bônus
    assert res["note"] >= 90


def test_poor_history(tmp_path):
    _init_repo(tmp_path)
    _commit(tmp_path, "a.py", "wip")
    res = check_git(tmp_path, "x-y", GitConfig())
    assert res["sub"]["commit_count"] == 50  # só 1 commit
    assert res["sub"]["semver_tag"] == 0     # sem tag
    assert res["sub"]["msg_quality"] == 0    # mensagem trivial


def test_no_repo(tmp_path):
    res = check_git(tmp_path, "x-y", GitConfig())
    assert res["note"] == 0
