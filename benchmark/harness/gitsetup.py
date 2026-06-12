"""Configura cada projeto gerado como um repo git INDEPENDENTE, isolado do repo raiz.

O `.git` aninhado vive sob runs/<slug>/app/ (gitignored no raiz → zero interferência). O remoto
aponta para o mesmo GitHub do benchmark; o push do agente vai para run/<slug> com tags namespaced.
"""

from __future__ import annotations

from pathlib import Path

from benchmark.harness.adapters.base import run_command
from benchmark.harness.config import GitConfig


def init_nested_repo(app_dir: Path, slug: str, git: GitConfig) -> dict:
    """Inicializa o repo aninhado e configura branch/remote conforme a política do benchmark."""
    app_dir.mkdir(parents=True, exist_ok=True)
    info: dict = {"slug": slug, "remote_configured": False, "push_enabled": git.push_enabled}

    branch = f"{git.branch_prefix}{slug}"

    steps = [
        ["git", "init", "-q"],
        # O agente trabalha já na branch run/<slug> — assim um `git push origin HEAD` dele
        # vai para run/<slug>, NUNCA para o main do repo do benchmark.
        ["git", "checkout", "-q", "-B", branch],
        ["git", "config", "user.name", f"benchmark-{slug}"],
        ["git", "config", "user.email", f"{slug}@benchmark.local"],
        ["git", "config", "benchmark.slug", slug],
        ["git", "config", "benchmark.targetBranch", branch],
    ]
    for cmd in steps:
        rc, _out, err, _ = run_command(cmd, cwd=app_dir, timeout=60)
        if rc != 0:
            info["error"] = f"{' '.join(cmd)} -> {err.strip()}"
            return info

    # O origin real só é configurado quando o push está habilitado. Com push desabilitado,
    # o `git push` do agente falha de forma inofensiva (não toca o repo compartilhado).
    if git.push_enabled and git.github_remote:
        rc, _o, _e, _ = run_command(["git", "remote", "add", "origin", git.github_remote],
                                    cwd=app_dir, timeout=60)
        info["remote_configured"] = rc == 0
        info["remote"] = git.github_remote
        info["target_branch"] = branch
        info["tag_namespace"] = slug if git.tag_namespace else None

    return info


def push_results(app_dir: Path, slug: str, git: GitConfig) -> dict:
    """Empurra o trabalho do agente para run/<slug> e tags namespaced (se push habilitado).

    Chamado pelo harness após a Fase 3 como rede de segurança/normalização — o agente também
    tenta `git push` por conta própria (isso faz parte do critério de avaliação).
    """
    result: dict = {"attempted": False, "branch_ok": False, "tags_ok": False}
    if not (git.push_enabled and git.github_remote):
        result["skipped"] = "push desabilitado ou sem remoto"
        return result

    result["attempted"] = True
    branch = f"{git.branch_prefix}{slug}"

    rc, _o, err, _ = run_command(["git", "push", "origin", f"HEAD:{branch}", "--force"],
                                 cwd=app_dir, timeout=300)
    result["branch_ok"] = rc == 0
    if rc != 0:
        result["branch_error"] = err.strip()[-500:]

    # tags namespaced: refs/tags/* -> refs/tags/<slug>/*
    if git.tag_namespace:
        rc, _o, err, _ = run_command(
            ["git", "push", "origin", f"refs/tags/*:refs/tags/{slug}/*", "--force"],
            cwd=app_dir, timeout=300,
        )
    else:
        rc, _o, err, _ = run_command(["git", "push", "origin", "--tags", "--force"],
                                     cwd=app_dir, timeout=300)
    result["tags_ok"] = rc == 0
    if rc != 0:
        result["tags_error"] = err.strip()[-500:]

    return result
