"""Adapter para o OpenAI Codex CLI (conta ChatGPT, modo não-interativo `codex exec`)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from benchmark.harness.adapters.base import Adapter, PhaseResult, run_command

CODEX_BIN = shutil.which("codex") or "codex"
_SESSION_RE = re.compile(r"session id:\s*([0-9a-fA-F-]{36})")
_TOKENS_RE = re.compile(r"tokens used[\s:]*([\d.,]+)")


def _extract_session(text: str) -> str | None:
    m = _SESSION_RE.search(text)
    return m.group(1) if m else None


class CodexCliAdapter(Adapter):
    name = "codex_cli"

    def _exec_cmd(self, workdir: Path) -> list[str]:
        # prompt via stdin (arg "-"); bypass de aprovação/sandbox para build autônomo
        return [CODEX_BIN, "exec", "-m", self.model,
                "--dangerously-bypass-approvals-and-sandbox", "-C", str(workdir), "-"]

    def _resume_cmd(self, workdir: Path, session_id: str) -> list[str]:
        return [CODEX_BIN, "exec", "resume", session_id,
                "--dangerously-bypass-approvals-and-sandbox", "-C", str(workdir), "-"]

    def _result(self, phase: str, rc: int, out: str, err: str, dur: float,
                prev_sid: str | None = None) -> PhaseResult:
        blob = out + err
        sid = _extract_session(blob) or prev_sid
        tokens = None
        m = _TOKENS_RE.search(blob)
        if m:
            tokens = m.group(1)
        return PhaseResult(phase=phase, ok=(rc == 0), returncode=rc, stdout=out, stderr=err,
                           duration_s=dur, session_id=sid, extra={"tokens": tokens})

    def build(self, prompt: str, workdir: Path, env: dict) -> PhaseResult:
        rc, out, err, dur = run_command(self._exec_cmd(workdir), cwd=workdir, env=env,
                                        timeout=5400, stdin_text=prompt)
        return self._result("build", rc, out, err, dur)

    def continue_session(self, phase: str, prompt: str, workdir: Path, env: dict,
                         prev: PhaseResult) -> PhaseResult:
        if prev.session_id:
            rc, out, err, dur = run_command(self._resume_cmd(workdir, prev.session_id),
                                            cwd=workdir, env=env, timeout=5400, stdin_text=prompt)
            # se o resume falhar, cai para um exec novo na mesma pasta (arquivos já estão lá)
            if rc != 0:
                rc, out, err, dur = run_command(self._exec_cmd(workdir), cwd=workdir, env=env,
                                                timeout=5400, stdin_text=prompt)
        else:
            rc, out, err, dur = run_command(self._exec_cmd(workdir), cwd=workdir, env=env,
                                            timeout=5400, stdin_text=prompt)
        return self._result(phase, rc, out, err, dur, prev_sid=prev.session_id)
