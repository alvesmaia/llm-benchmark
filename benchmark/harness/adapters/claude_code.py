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


class ClaudeCodeAdapter(Adapter):
    name = "claude_code"

    def _base_cmd(self) -> list[str]:
        return [
            CLAUDE_BIN,
            "--model", self.model,
            "--output-format", "json",
            "--dangerously-skip-permissions",
            "-p",
        ]

    def _run(self, phase: str, prompt: str, workdir: Path, env: dict,
             resume: str | None = None) -> PhaseResult:
        cmd = self._base_cmd()
        if resume:
            # continua a sessão pelo id capturado na fase anterior
            cmd = [CLAUDE_BIN, "--model", self.model, "--output-format", "json",
                   "--dangerously-skip-permissions", "--resume", resume, "-p"]
        cmd = cmd + [prompt]
        rc, out, err, dur = run_command(cmd, cwd=workdir, env=env, timeout=env.get("_TIMEOUT", 5400)
                                        if isinstance(env, dict) and "_TIMEOUT" in env else 5400)
        data = _parse_json_output(out)
        return PhaseResult(
            phase=phase,
            ok=(rc == 0 and not data.get("is_error", False)),
            returncode=rc,
            stdout=out,
            stderr=err,
            duration_s=dur,
            session_id=data.get("session_id"),
            cost_usd=data.get("total_cost_usd"),
            extra={"num_turns": data.get("num_turns"), "result": (data.get("result") or "")[:2000]},
        )

    def build(self, prompt: str, workdir: Path, env: dict) -> PhaseResult:
        return self._run("build", prompt, workdir, env)

    def continue_session(self, phase: str, prompt: str, workdir: Path, env: dict,
                         prev: PhaseResult) -> PhaseResult:
        # Preferimos --resume <session_id>; se ausente, caímos para --continue.
        if prev.session_id:
            return self._run(phase, prompt, workdir, env, resume=prev.session_id)
        cmd = [CLAUDE_BIN, "--model", self.model, "--output-format", "json",
               "--dangerously-skip-permissions", "--continue", "-p", prompt]
        rc, out, err, dur = run_command(cmd, cwd=workdir, env=env, timeout=5400)
        data = _parse_json_output(out)
        return PhaseResult(phase=phase, ok=(rc == 0 and not data.get("is_error", False)),
                           returncode=rc, stdout=out, stderr=err, duration_s=dur,
                           session_id=data.get("session_id") or prev.session_id,
                           cost_usd=data.get("total_cost_usd"))
