"""Juiz E2E "funciona como usuário": sobe a app do candidato via `uvx` e pede a um agente Sonnet
(com Playwright MCP) que percorra a UI — login, dashboard, e tentar uma ação restrita (esperar
bloqueio). O agente retorna um JSON de veredito que vira a nota objetiva da dimensão `e2e`.

Robustez: se o Playwright MCP estiver indisponível (headless/cron) ou a app não subir, retorna
`{note: None, ...}` e o pipeline segue (a dimensão `e2e` cai para fallback do juiz/score).
NÃO é exercido pelo `selftest` (que não chama juízes/MCP).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

from benchmark.harness.adapters.base import run_command
from benchmark.harness.config import Config

QA_CHECKLIST = """\
Você é um QA automatizado. Use as ferramentas do **Playwright MCP** (browser_navigate,
browser_snapshot, browser_click, browser_type, browser_fill_form, browser_take_screenshot, etc.)
para usar a aplicação web como um usuário real e verificar se ela FUNCIONA. NÃO inspecione o código;
apenas dirija o browser pelas ferramentas do Playwright.

URL base: {base}
Credenciais admin: usuário={admin_user} senha={admin_password}
Credenciais viewer (papel sem permissão de escrita): usuário={viewer_user} senha={viewer_password}

Passos (registre o resultado de cada um):
1. Abrir a página inicial ({base}/) e confirmar que há um formulário de login.
2. Fazer login como admin e confirmar que entra/recebe sucesso.
3. Navegar ao dashboard/listagem de ativos e confirmar que métricas/telas renderizam.
4. Tentar uma ação restrita (escrita/admin) com o papel SEM permissão (viewer) e confirmar que é
   BLOQUEADA (403 ou mensagem de acesso negado na UI).

Responda APENAS com JSON válido, sem texto fora do JSON:
{{"steps": [{{"nome": "...", "ok": true, "detalhe": "..."}}], "works": true, "issues": ["..."]}}
"""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _console_script(app_dir: Path) -> str:
    pp = app_dir / "pyproject.toml"
    if pp.exists():
        txt = pp.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^\s*([\w-]+)\s*=\s*[\"'][\w_]+(?:\.[\w_]+)*:", txt, re.MULTILINE)
        if m:
            return m.group(1)
    return "it-assets"


def _extract_json(text: str) -> dict | None:
    text = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # claude --output-format json embrulha em {"result": "..."}
    try:
        wrapped = json.loads(text)
        if isinstance(wrapped, dict) and isinstance(wrapped.get("result"), str):
            inner = _extract_json(wrapped["result"])
            if inner:
                return inner
        if isinstance(wrapped, dict) and "steps" in wrapped:
            return wrapped
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def parse_verdict(raw: str) -> dict:
    """Converte a saída do agente E2E em {note, works, steps, issues}. note = % de passos OK."""
    data = _extract_json(raw)
    if not data or "steps" not in data or not isinstance(data["steps"], list):
        return {"note": None, "error": "veredito E2E não parseável", "raw_tail": (raw or "")[-400:]}
    steps = data["steps"]
    total = len(steps)
    ok = sum(1 for s in steps if isinstance(s, dict) and s.get("ok") is True)
    note = round(100 * ok / total, 1) if total else None
    return {
        "note": note,
        "works": bool(data.get("works")),
        "steps": steps,
        "issues": data.get("issues", []),
        "ok_steps": ok,
        "total_steps": total,
    }


def _boot_app(app_dir: Path, env: dict, script: str) -> tuple[subprocess.Popen | None, str | None]:
    port = _free_port()
    try:
        proc = subprocess.Popen(
            ["uvx", "--from", str(app_dir), script, "serve", "--host", "127.0.0.1",
             "--port", str(port)],
            cwd=str(app_dir), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except (OSError, FileNotFoundError):
        return None, None
    import httpx
    base = None
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline and base is None:
        try:
            httpx.get(f"http://127.0.0.1:{port}/", timeout=2)
            base = f"http://127.0.0.1:{port}"
        except httpx.HTTPError:
            time.sleep(1)
    if base is None:
        proc.terminate()
        return None, None
    return proc, base


def run_e2e(app_dir: Path, logs_dir: Path, scenario, cfg: Config) -> dict:
    """Roda o juiz E2E. Sempre retorna um dict; nunca levanta. Salva logs/e2e_playwright.json."""
    e2e_cfg = (cfg.raw.get("e2e_judge") or {}) if hasattr(cfg, "raw") else {}
    result: dict = {"note": None, "agent": e2e_cfg.get("agent"), "model": e2e_cfg.get("model")}
    out_file = logs_dir / "e2e_playwright.json"

    if not e2e_cfg:
        result["skipped"] = "e2e_judge não configurado em config.yaml"
        out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    env = dict(os.environ)
    env.update(scenario.extra_env)
    env["PYTHONIOENCODING"] = "utf-8"
    script = _console_script(app_dir)

    proc, base = _boot_app(app_dir, env, script)
    if base is None:
        result["error"] = "app não subiu via uvx (E2E pulado)"
        out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    try:
        prompt = QA_CHECKLIST.format(
            base=base,
            admin_user=scenario.extra_env.get("ADMIN_USER", "admin"),
            admin_password=scenario.extra_env.get("ADMIN_PASSWORD", "admin123"),
            viewer_user=scenario.extra_env.get("VIEWER_USER", "viewer"),
            viewer_password=scenario.extra_env.get("VIEWER_PASSWORD", "viewer123"),
        )
        raw = _invoke_playwright_agent(e2e_cfg, prompt, app_dir)
        verdict = parse_verdict(raw)
        result.update(verdict)
        result["base"] = base
    except Exception as e:  # noqa: BLE001 - robustez: nunca derruba o pipeline
        result["error"] = f"falha no agente E2E: {e}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _invoke_playwright_agent(e2e_cfg: dict, prompt: str, cwd: Path) -> str:
    """Invoca o agente (claude_code Sonnet) com o Playwright MCP. Se o CLI/MCP estiver
    indisponível, levanta — o chamador captura e cai para o fallback."""
    agent = e2e_cfg.get("agent", "claude_code")
    model = e2e_cfg.get("model", "sonnet")
    if agent != "claude_code":
        raise RuntimeError(f"juiz E2E só suporta claude_code (recebido: {agent})")
    claude = shutil.which("claude") or "claude"
    # habilita o Playwright MCP explicitamente p/ o agente spawnado (headless), sem depender de
    # plugins do ambiente. Com --dangerously-skip-permissions as tools do MCP são auto-aprovadas.
    mcp_config = json.dumps({
        "mcpServers": {
            "playwright": {
                "command": "npx",
                "args": ["-y", "@playwright/mcp@latest", "--headless"],
            },
        }
    })
    cmd = [claude, "--model", model, "--output-format", "json",
           "--mcp-config", mcp_config,
           "--dangerously-skip-permissions", "-p"]
    rc, out, err, _ = run_command(cmd, cwd=cwd, timeout=1200, stdin_text=prompt)
    if rc != 0 and not out:
        raise RuntimeError(f"agente E2E falhou (rc={rc}): {err[-300:]}")
    return out
