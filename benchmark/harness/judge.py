"""Painel de juízes (Claude Opus + Copilot GPT). Cada juiz pontua a rubrica; tiramos a média.

Reduz viés: dois modelos diferentes avaliam de forma independente. Cada juiz NÃO pontua o output
gerado pelo seu próprio par agente/modelo (anti-auto-favorecimento).
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from benchmark.harness.adapters.base import run_command
from benchmark.harness.config import REPO_ROOT, Config, Judge
from benchmark.harness.rubric import DIMENSIONS

MAX_FILE_BYTES = 6000
CODE_GLOBS = ["*.py", "Dockerfile", "docker-compose.y*ml", "pyproject.toml"]
SKIP_DIRS = {".git", ".venv", "__pycache__", ".ruff_cache", ".pytest_cache", "node_modules"}


def _file_tree(app_dir: Path, limit: int = 200) -> str:
    lines = []
    for p in sorted(app_dir.rglob("*")):
        if any(part in SKIP_DIRS for part in p.relative_to(app_dir).parts):
            continue
        if p.is_file():
            lines.append(str(p.relative_to(app_dir)).replace("\\", "/"))
        if len(lines) >= limit:
            lines.append("... (truncado)")
            break
    return "\n".join(lines)


def _code_excerpts(app_dir: Path, max_files: int = 14) -> str:
    chunks = []
    seen = 0
    for pattern in CODE_GLOBS:
        for p in sorted(app_dir.rglob(pattern)):
            if any(part in SKIP_DIRS for part in p.relative_to(app_dir).parts):
                continue
            if seen >= max_files:
                break
            try:
                text = p.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_BYTES]
            except OSError:
                continue
            rel = str(p.relative_to(app_dir)).replace("\\", "/")
            chunks.append(f"--- {rel} ---\n{text}")
            seen += 1
    return "\n\n".join(chunks)


def _git_log(app_dir: Path) -> str:
    if not (app_dir / ".git").exists():
        return "(sem repositório git)"
    rc, out, _e, _ = run_command(["git", "log", "--pretty=%h %s", "-n", "30"],
                                 cwd=app_dir, timeout=60)
    _rc2, tags, _e2, _ = run_command(["git", "tag", "--list"], cwd=app_dir, timeout=60)
    return f"COMMITS:\n{out.strip()}\n\nTAGS:\n{tags.strip()}"


def build_prompt(template: str, *, app_dir: Path, objective: dict) -> str:
    brief = (REPO_ROOT / "benchmark" / "brief" / "challenge.md").read_text(encoding="utf-8")
    rubric = (REPO_ROOT / "benchmark" / "rubric" / "rubric.md").read_text(encoding="utf-8")
    repl = {
        "{{BRIEF}}": brief,
        "{{RUBRIC}}": rubric,
        "{{OBJECTIVE_RESULTS}}": json.dumps(objective, ensure_ascii=False, indent=2)[:8000],
        "{{FILE_TREE}}": _file_tree(app_dir),
        "{{CODE_EXCERPTS}}": _code_excerpts(app_dir),
        "{{GIT_LOG}}": _git_log(app_dir),
    }
    out = template
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    # bloco ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # primeiro { ... último }
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _invoke_judge(judge: Judge, prompt: str, cwd: Path) -> dict:
    """Invoca o CLI do juiz em modo print e parseia o JSON de notas."""
    if judge.agent == "claude_code":
        claude = shutil.which("claude") or "claude"
        cmd = [claude, "--model", judge.model, "--output-format", "json",
               "--dangerously-skip-permissions", "-p", prompt]
        rc, out, err, _ = run_command(cmd, cwd=cwd, timeout=1200)
        # claude --output-format json embrulha em {result: "..."}; pegamos o result
        wrapped = _extract_json(out)
        inner = None
        if wrapped and "result" in wrapped and isinstance(wrapped["result"], str):
            inner = _extract_json(wrapped["result"])
        scores = inner or wrapped or _extract_json(out)
    elif judge.agent == "copilot_cli":
        copilot = shutil.which("copilot") or "copilot"
        cmd = [copilot, "-p", prompt, "--model", judge.model, "--allow-all-tools"]
        rc, out, err, _ = run_command(cmd, cwd=cwd, timeout=1200)
        scores = _extract_json(out)
    else:
        return {"error": f"juiz desconhecido: {judge.agent}"}

    if not scores or "scores" not in scores:
        return {"error": "não foi possível parsear JSON do juiz", "raw_tail": (out or err)[-500:]}
    return scores


def run_panel(app_dir: Path, candidate_slug: str, objective: dict, cfg: Config) -> dict:
    """Roda todos os juízes, aplica anti-auto-favorecimento e calcula a média por dimensão."""
    template = (REPO_ROOT / "benchmark" / "rubric" / "judge_prompt.md").read_text(encoding="utf-8")
    prompt = build_prompt(template, app_dir=app_dir, objective=objective)

    per_judge = {}
    for judge in cfg.judges:
        judge_candidate_slug = f"{judge.agent}-{_judge_model_slug(judge, cfg)}"
        if judge_candidate_slug == candidate_slug:
            per_judge[judge.id] = {
                "skipped": "anti-auto-favorecimento (mesmo agente/modelo do avaliado)"}
            continue
        per_judge[judge.id] = _invoke_judge(judge, prompt, cwd=app_dir)

    # média por dimensão entre juízes válidos
    averaged = {}
    divergences = {}
    for dim in DIMENSIONS:
        notes = []
        for _jid, res in per_judge.items():
            if "scores" in res and isinstance(res["scores"].get(dim), (int, float)):
                notes.append(float(res["scores"][dim]))
        if notes:
            averaged[dim] = round(sum(notes) / len(notes), 1)
            if len(notes) >= 2 and (max(notes) - min(notes)) > cfg.divergence_flag_threshold:
                divergences[dim] = {"spread": round(max(notes) - min(notes), 1), "notes": notes}
        else:
            averaged[dim] = None  # sem juiz válido para esta dimensão

    hallucinated = any(res.get("hallucinated_dependency") for res in per_judge.values()
                       if isinstance(res, dict))

    return {
        "per_judge": per_judge,
        "averaged_by_dimension": averaged,
        "divergences": divergences,
        "hallucinated_dependency_votes": hallucinated,
    }


def _judge_model_slug(judge: Judge, cfg: Config) -> str:
    """Mapeia o juiz para o model_slug do candidato correspondente, se existir na matriz."""
    for c in cfg.candidates:
        if c.agent == judge.agent and c.model == judge.model:
            return c.model_slug
    return judge.model
