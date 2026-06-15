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
    # custo detalhado de tokens (quando o CLI reporta de forma estruturada)
    tokens_input: int | None = None
    tokens_output: int | None = None
    tokens_cache_write: int | None = None
    tokens_cache_read: int | None = None
    interactions: int | None = None  # nº de turns/passos do agente na fase (quando o CLI reporta)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "ok": self.ok,
            "returncode": self.returncode,
            "duration_s": round(self.duration_s, 2),
            "session_id": self.session_id,
            "cost_usd": self.cost_usd,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "tokens_cache_write": self.tokens_cache_write,
            "tokens_cache_read": self.tokens_cache_read,
            "interactions": self.interactions,
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

    def __init__(self, model: str, effort: str | None = None):
        self.model = model
        self.effort = effort  # nível de esforço de raciocínio (quando o CLI suporta)

    def build(self, prompt: str, workdir: Path, env: dict) -> PhaseResult:
        """Fase 1: construir o projeto a partir do prompt, dentro de workdir."""
        raise NotImplementedError

    def continue_session(self, phase: str, prompt: str, workdir: Path, env: dict,
                         prev: PhaseResult) -> PhaseResult:
        """Fases 2/3: continuar a mesma sessão do agente."""
        raise NotImplementedError


def get_adapter(agent: str, model: str, effort: str | None = None) -> Adapter:
    # import tardio para evitar ciclos
    from benchmark.harness.adapters.claude_code import ClaudeCodeAdapter
    from benchmark.harness.adapters.codex_cli import CodexCliAdapter
    from benchmark.harness.adapters.copilot_cli import CopilotCliAdapter
    from benchmark.harness.adapters.opencode_cli import OpenCodeCliAdapter

    mapping = {
        "claude_code": ClaudeCodeAdapter,
        "copilot_cli": CopilotCliAdapter,
        "codex_cli": CodexCliAdapter,
        "opencode": OpenCodeCliAdapter,
    }
    if agent not in mapping:
        raise ValueError(f"agente desconhecido: {agent} (conhecidos: {list(mapping)})")
    return mapping[agent](model, effort=effort)
