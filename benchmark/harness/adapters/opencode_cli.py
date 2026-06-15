"""Adapter para o opencode CLI (modo headless `opencode run`, saída NDJSON via --format json)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from benchmark.harness.adapters.base import Adapter, PhaseResult, run_command

OPENCODE_BIN = shutil.which("opencode") or "opencode"


def _parse_events(stdout: str) -> tuple[str | None, float | None, dict]:
    """O `--format json` emite um evento JSON por linha. Extrai o sessionID, soma o custo dos
    eventos `step_finish` (cada passo reporta seu próprio `cost`) e soma o `tokens` de cada passo
    (`input`/`output`/`cache.write`/`cache.read`)."""
    session_id: str | None = None
    cost = 0.0
    saw_cost = False
    tok = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    saw_tok = False
    for line in stdout.splitlines():
        line = line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = session_id or ev.get("sessionID")
        part = ev.get("part") or {}
        if ev.get("type") == "step_finish":
            if isinstance(part.get("cost"), (int, float)):
                cost += float(part["cost"])
                saw_cost = True
            tokens = part.get("tokens") or {}
            if isinstance(tokens, dict):
                cache = tokens.get("cache") or {}
                for src, dst in (("input", "input"), ("output", "output")):
                    v = tokens.get(src)
                    if isinstance(v, (int, float)):
                        tok[dst] += int(v)
                        saw_tok = True
                if isinstance(cache, dict):
                    for src, dst in (("write", "cache_write"), ("read", "cache_read")):
                        v = cache.get(src)
                        if isinstance(v, (int, float)):
                            tok[dst] += int(v)
                            saw_tok = True
    usage = {
        "tokens_input": tok["input"] if saw_tok else None,
        "tokens_output": tok["output"] if saw_tok else None,
        "tokens_cache_write": tok["cache_write"] if saw_tok else None,
        "tokens_cache_read": tok["cache_read"] if saw_tok else None,
    }
    return session_id, (round(cost, 6) if saw_cost else None), usage


class OpenCodeCliAdapter(Adapter):
    name = "opencode"

    def _base_cmd(self) -> list[str]:
        # modelo no formato provider/model; permissões auto-aprovadas para build autônomo
        return [OPENCODE_BIN, "run", "-m", self.model, "--format", "json",
                "--dangerously-skip-permissions"]

    def _resume_cmd(self, session_id: str) -> list[str]:
        return [OPENCODE_BIN, "run", "-s", session_id, "-m", self.model, "--format", "json",
                "--dangerously-skip-permissions"]

    def _run(self, phase: str, cmd: list[str], prompt: str, workdir: Path, env: dict,
             prev_sid: str | None = None) -> PhaseResult:
        # prompt via stdin (Regra 2 — evita o limite de linha de comando do Windows)
        rc, out, err, dur = run_command(cmd, cwd=workdir, env=env, timeout=5400, stdin_text=prompt)
        sid, cost, usage = _parse_events(out)
        return PhaseResult(
            phase=phase, ok=(rc == 0), returncode=rc, stdout=out, stderr=err,
            duration_s=dur, session_id=sid or prev_sid, cost_usd=cost, **usage,
            extra={"result": (out or "")[-2000:]},
        )

    def build(self, prompt: str, workdir: Path, env: dict) -> PhaseResult:
        return self._run("build", self._base_cmd(), prompt, workdir, env)

    def continue_session(self, phase: str, prompt: str, workdir: Path, env: dict,
                         prev: PhaseResult) -> PhaseResult:
        if prev.session_id:
            res = self._run(phase, self._resume_cmd(prev.session_id), prompt, workdir, env,
                            prev_sid=prev.session_id)
            # se o resume falhar, cai para um run novo na mesma pasta (arquivos já estão lá)
            if res.ok:
                return res
        return self._run(phase, self._base_cmd(), prompt, workdir, env,
                         prev_sid=prev.session_id)
