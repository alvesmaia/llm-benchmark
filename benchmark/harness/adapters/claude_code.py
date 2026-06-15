"""Adapter para o Claude Code CLI (assinatura mensal, modo headless `-p`)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from benchmark.harness.adapters.base import Adapter, PhaseResult, run_command

CLAUDE_BIN = shutil.which("claude") or "claude"


def _parse_json_output(stdout: str) -> dict:
    """O `--output-format json` emite um objeto JSON com result/session_id/cost/duração."""
    stdout = stdout.strip()
    if not stdout:
        return {}
    # Tenta o último bloco JSON da saída (robusto a logs antes do JSON).
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
    return {}


def _tokens(data: dict) -> dict:
    """Extrai o custo detalhado de tokens do bloco `usage` do JSON do Claude Code."""
    usage = data.get("usage") or {}
    if not isinstance(usage, dict):
        return {}
    def _i(key):
        v = usage.get(key)
        return int(v) if isinstance(v, (int, float)) else None
    return {
        "tokens_input": _i("input_tokens"),
        "tokens_output": _i("output_tokens"),
        "tokens_cache_write": _i("cache_creation_input_tokens"),
        "tokens_cache_read": _i("cache_read_input_tokens"),
    }


class ClaudeCodeAdapter(Adapter):
    name = "claude_code"

    def _effort_args(self) -> list[str]:
        return ["--effort", self.effort] if self.effort else []

    def _base_cmd(self) -> list[str]:
        return [
            CLAUDE_BIN,
            "--model", self.model,
            *self._effort_args(),
            "--output-format", "json",
            "--dangerously-skip-permissions",
            "-p",
        ]

    def _run(self, phase: str, prompt: str, workdir: Path, env: dict,
             resume: str | None = None) -> PhaseResult:
        cmd = self._base_cmd()
        if resume:
            # continua a sessão pelo id capturado na fase anterior
            cmd = [CLAUDE_BIN, "--model", self.model, *self._effort_args(),
                   "--output-format", "json",
                   "--dangerously-skip-permissions", "--resume", resume, "-p"]
        # prompt via stdin (evita o limite de tamanho de linha de comando do Windows)
        rc, out, err, dur = run_command(cmd, cwd=workdir, env=env, timeout=5400, stdin_text=prompt)
        data = _parse_json_output(out)
        usage = _tokens(data)
        return PhaseResult(
            phase=phase,
            ok=(rc == 0 and not data.get("is_error", False)),
            returncode=rc,
            stdout=out,
            stderr=err,
            duration_s=dur,
            session_id=data.get("session_id"),
            cost_usd=data.get("total_cost_usd"),
            **usage,
            extra={"num_turns": data.get("num_turns"), "result": (data.get("result") or "")[:2000]},
        )

    def build(self, prompt: str, workdir: Path, env: dict) -> PhaseResult:
        return self._run("build", prompt, workdir, env)

    def continue_session(self, phase: str, prompt: str, workdir: Path, env: dict,
                         prev: PhaseResult) -> PhaseResult:
        # Preferimos --resume <session_id>; se ausente, caímos para --continue.
        if prev.session_id:
            return self._run(phase, prompt, workdir, env, resume=prev.session_id)
        cmd = [CLAUDE_BIN, "--model", self.model, *self._effort_args(),
               "--output-format", "json",
               "--dangerously-skip-permissions", "--continue", "-p"]
        rc, out, err, dur = run_command(cmd, cwd=workdir, env=env, timeout=5400, stdin_text=prompt)
        data = _parse_json_output(out)
        return PhaseResult(phase=phase, ok=(rc == 0 and not data.get("is_error", False)),
                           returncode=rc, stdout=out, stderr=err, duration_s=dur,
                           session_id=data.get("session_id") or prev.session_id,
                           cost_usd=data.get("total_cost_usd"), **_tokens(data))
