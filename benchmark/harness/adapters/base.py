"""Interface comum dos adapters e utilitários de subprocesso."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PhaseResult:
    phase: str
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    session_id: str | None = None
    cost_usd: float | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "ok": self.ok,
            "returncode": self.returncode,
            "duration_s": round(self.duration_s, 2),
            "session_id": self.session_id,
            "cost_usd": self.cost_usd,
            "stdout_tail": self.stdout[-4000:],
            "stderr_tail": self.stderr[-2000:],
            "extra": self.extra,
        }


def run_command(
    cmd: list[str],
    cwd: Path,
    env: dict | None = None,
    timeout: int = 3600,
    stdin_text: str | None = None,
) -> tuple[int, str, str, float]:
    """Roda um comando capturando stdout/stderr. Retorna (rc, out, err, duração)."""
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            input=stdin_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or "", time.monotonic() - start
    except subprocess.TimeoutExpired as e:
        def _dec(v):
            return v.decode("utf-8", "replace") if isinstance(v, bytes) else (v or "")

        out, err = _dec(e.stdout), _dec(e.stderr)
        return 124, out, f"{err}\n[TIMEOUT após {timeout}s]", time.monotonic() - start
    except FileNotFoundError as e:
        return 127, "", f"comando não encontrado: {e}", time.monotonic() - start


class Adapter:
    """Base para adapters de code agents. Cada um dirige seu CLI em modo headless."""

    name: str = "base"

    def __init__(self, model: str):
        self.model = model

    def build(self, prompt: str, workdir: Path, env: dict) -> PhaseResult:
        """Fase 1: construir o projeto a partir do prompt, dentro de workdir."""
        raise NotImplementedError

    def continue_session(self, phase: str, prompt: str, workdir: Path, env: dict,
                         prev: PhaseResult) -> PhaseResult:
        """Fases 2/3: continuar a mesma sessão do agente."""
        raise NotImplementedError


def get_adapter(agent: str, model: str) -> Adapter:
    # import tardio para evitar ciclos
    from benchmark.harness.adapters.claude_code import ClaudeCodeAdapter
    from benchmark.harness.adapters.codex_cli import CodexCliAdapter
    from benchmark.harness.adapters.copilot_cli import CopilotCliAdapter

    mapping = {
        "claude_code": ClaudeCodeAdapter,
        "copilot_cli": CopilotCliAdapter,
        "codex_cli": CodexCliAdapter,
    }
    if agent not in mapping:
        raise ValueError(f"agente desconhecido: {agent} (conhecidos: {list(mapping)})")
    return mapping[agent](model)
