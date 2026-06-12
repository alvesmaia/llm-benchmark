"""Adapter para o GitHub Copilot CLI (assinatura mensal, modo não-interativo `-p`)."""

from __future__ import annotations

import shutil
from pathlib import Path

from benchmark.harness.adapters.base import Adapter, PhaseResult, run_command

# No Windows o copilot pode ser um .ps1; resolvemos o executável real quando possível.
COPILOT_BIN = shutil.which("copilot") or "copilot"


class CopilotCliAdapter(Adapter):
    name = "copilot_cli"

    def _cmd(self, prompt: str, resume: bool = False) -> list[str]:
        cmd = [COPILOT_BIN, "-p", prompt, "--model", self.model, "--allow-all-tools"]
        if resume:
            cmd = [COPILOT_BIN, "--continue", "-p", prompt, "--model", self.model,
                   "--allow-all-tools"]
        return cmd

    def _run(self, phase: str, prompt: str, workdir: Path, env: dict,
             resume: bool = False) -> PhaseResult:
        cmd = self._cmd(prompt, resume=resume)
        rc, out, err, dur = run_command(cmd, cwd=workdir, env=env, timeout=5400)
        return PhaseResult(
            phase=phase,
            ok=(rc == 0),
            returncode=rc,
            stdout=out,
            stderr=err,
            duration_s=dur,
            extra={"result": (out or "")[-2000:]},
        )

    def build(self, prompt: str, workdir: Path, env: dict) -> PhaseResult:
        return self._run("build", prompt, workdir, env)

    def continue_session(self, phase: str, prompt: str, workdir: Path, env: dict,
                         prev: PhaseResult) -> PhaseResult:
        return self._run(phase, prompt, workdir, env, resume=True)
