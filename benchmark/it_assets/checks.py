"""Checagens objetivas do cenário `it_assets` (caixa-preta via `uv run` / `uvx` / HTTP).

Estrutura interna do projeto é livre; só o contrato mínimo (challenge.md) é verificado. Cada
checagem retorna 0-100 e mapeia para uma dimensão da rubrica. Falhas degradam para 0 com detalhe —
nunca derrubam o harness. As checagens rodam no **estado final** (pós-Fase 3, base já mutada),
então `pytest_coverage`/`execucao_uvx` passando = a app se recuperou (dimensão `resiliencia`).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import time
from pathlib import Path

import httpx

from benchmark.harness.checks import CheckResult, _free_port, _uv, check_readme, check_ruff

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
VIEWER_USER = os.environ.get("VIEWER_USER", "viewer")
VIEWER_PASSWORD = os.environ.get("VIEWER_PASSWORD", "viewer123")

CONSOLE_SCRIPT = "it-assets"
# limiar de cobertura usado SÓ no harness (não revelado ao candidato):
# nota = min(100, cov / limiar * 100)
COVERAGE_TARGET = 75.0


def _resolve_dataset(app_dir: Path, dataset_path: Path) -> Path:
    """Avaliação roda no estado FINAL: se o projeto tem a base copiada em `data/` (mutada pela
    perturbação da Fase 3), a checagem usa ESSA cópia — é o que a app robusta precisa ingerir.
    Senão, cai para o dataset canônico do harness."""
    data_dir = app_dir / "data"
    if data_dir.exists():
        csvs = sorted((p for p in data_dir.rglob("*.csv")), key=lambda p: p.stat().st_size,
                      reverse=True)
        if csvs:
            return csvs[0]
    return dataset_path


def _env(app_dir: Path, dataset_path: Path, db_path: Path) -> dict:
    env = dict(os.environ)
    env["DATASET_PATH"] = str(_resolve_dataset(app_dir, dataset_path))
    env["DB_PATH"] = str(db_path)
    env["ADMIN_USER"] = ADMIN_USER
    env["ADMIN_PASSWORD"] = ADMIN_PASSWORD
    env["VIEWER_USER"] = VIEWER_USER
    env["VIEWER_PASSWORD"] = VIEWER_PASSWORD
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _console_script(app_dir: Path) -> str:
    """Lê o console script declarado no pyproject; default `it-assets`."""
    pp = app_dir / "pyproject.toml"
    if pp.exists():
        txt = pp.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^\s*([\w-]+)\s*=\s*[\"'][\w_]+(?:\.[\w_]+)*:", txt, re.MULTILINE)
        if m:
            return m.group(1)
    return CONSOLE_SCRIPT


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _db_rows(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    try:
        con = sqlite3.connect(str(db_path))
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        total = 0
        for t in tables:
            if t.lower() == "users":
                continue
            try:
                total += con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            except sqlite3.Error:
                continue
        con.close()
        return total
    except sqlite3.Error:
        return 0


# ---------------------------------------------------------------------------
# Coverage / tests
# ---------------------------------------------------------------------------
def _extract_coverage(blob: str) -> float | None:
    """Captura a % total de cobertura da saída do pytest-cov/coverage report."""
    m = re.search(r"^TOTAL\s+.*?\s(\d+(?:\.\d+)?)%", blob, re.MULTILINE)
    if m:
        return float(m.group(1))
    # fallback: última ocorrência de "NN%" numa linha de total
    matches = re.findall(r"(\d+(?:\.\d+)?)%", blob)
    return float(matches[-1]) if matches else None


def check_pytest_coverage(app_dir: Path, env: dict) -> tuple[CheckResult, float | None]:
    """Roda pytest sob cobertura, confirma que passa E captura a % atingida. A nota de `tests` é
    proporcional à cobertura (alvo NÃO revelado ao candidato)."""
    # tenta com --cov; se o projeto não tiver pytest-cov, cai para pytest puro.
    rc, out, err, _ = _uv(["pytest", "-q", "--cov", "--cov-report=term"], app_dir, env, timeout=900)
    blob = out + err
    if "unrecognized arguments" in blob or "no module named pytest_cov" in blob.lower():
        rc, out, err, _ = _uv(["pytest", "-q"], app_dir, env, timeout=900)
        blob = out + err
    cov = _extract_coverage(blob)
    tests_pass = rc == 0
    if not tests_pass:
        m = re.search(r"(\d+) passed", blob)
        f = re.search(r"(\d+) failed", blob)
        passed = int(m.group(1)) if m else 0
        failed = int(f.group(1)) if f else 0
        total = passed + failed
        note = round(100 * passed / total, 1) if total else 0
        detail = f"{passed} passed / {failed} failed (rc={rc}); cobertura={cov}"
        return CheckResult("pytest_coverage", "tests", note, detail=detail), cov
    # passou: nota proporcional à cobertura medida (alvo interno COVERAGE_TARGET)
    if cov is not None:
        note = round(min(100.0, cov / COVERAGE_TARGET * 100.0), 1)
        detail = f"testes passam; cobertura={cov}% (nota proporcional)"
    else:
        note = 70.0  # passou mas sem medição de cobertura
        detail = "testes passam; cobertura não medida"
    return CheckResult("pytest_coverage", "tests", note, detail=detail), cov


# ---------------------------------------------------------------------------
# Execução via uvx (boot) + server checks
# ---------------------------------------------------------------------------
def _login(base: str, user: str, password: str) -> str | None:
    try:
        r = httpx.post(f"{base}/auth/login", json={"username": user, "password": password},
                       timeout=5)
        if r.status_code == 200:
            body = r.json()
            for key in ("token", "access_token", "jwt"):
                if isinstance(body, dict) and body.get(key):
                    return str(body[key])
    except (httpx.HTTPError, json.JSONDecodeError):
        return None
    return None


def _server_checks(app_dir: Path, env: dict, script: str) -> tuple[list[CheckResult], bool, float]:
    """Sobe a app pelo console script (uvx) numa porta livre e roda os checks HTTP."""
    port = _free_port()
    boot_start = time.monotonic()
    proc = subprocess.Popen(
        ["uvx", "--from", str(app_dir), script, "serve", "--host", "127.0.0.1",
         "--port", str(port)],
        cwd=str(app_dir), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = None
    boot_time = 0.0
    deadline = time.monotonic() + 90
    try:
        while time.monotonic() < deadline and base is None:
            try:
                httpx.get(f"http://127.0.0.1:{port}/", timeout=2)
                base = f"http://127.0.0.1:{port}"
                boot_time = time.monotonic() - boot_start
            except httpx.HTTPError:
                time.sleep(1)

        names_dims = {
            "uvx_boot": "execucao_uvx", "web_login_form": "api_web",
            "auth_login": "auth_jwt", "auth_required": "auth_jwt",
            "rbac_denied": "rbac", "api_dashboard": "api_web",
        }
        if base is None:
            return ([CheckResult(n, d, 0, "servidor não subiu via uvx")
                     for n, d in names_dims.items()], False, 0.0)

        results: list[CheckResult] = []
        results.append(CheckResult("uvx_boot", "execucao_uvx", 100,
                                   detail=f"app subiu via uvx em {boot_time:.1f}s"))

        # web_login_form
        try:
            r = httpx.get(base + "/", timeout=5)
            html = r.text.lower()
            ok = r.status_code == 200 and "<form" in html \
                and "username" in html and "password" in html
            results.append(CheckResult("web_login_form", "api_web", 100 if ok else 0,
                                       detail="form de login presente" if ok else "form ausente"))
        except httpx.HTTPError as e:
            results.append(CheckResult("web_login_form", "api_web", 0, f"erro: {e}"))

        # auth_login (válido vs inválido)
        token = _login(base, ADMIN_USER, ADMIN_PASSWORD)
        bad_status = None
        try:
            rb = httpx.post(f"{base}/auth/login",
                            json={"username": ADMIN_USER, "password": "senha_errada_xyz"},
                            timeout=5)
            bad_status = rb.status_code
        except httpx.HTTPError:
            bad_status = None
        login_ok = token is not None and bad_status == 401
        results.append(CheckResult("auth_login", "auth_jwt", 100 if login_ok else 0,
                                   detail=f"login válido={'ok' if token else 'falhou'}, "
                                          f"inválido->{bad_status}"))

        # auth_required: rota protegida SEM token -> 401/403
        protected = _find_protected_route(base, token)
        if protected is not None:
            path, payload = protected
            try:
                r = httpx.post(f"{base}{path}", json=payload, timeout=5)
                ok = r.status_code in (401, 403)
                results.append(CheckResult("auth_required", "auth_jwt", 100 if ok else 0,
                                           detail=f"POST {path} sem token -> {r.status_code}"))
            except httpx.HTTPError as e:
                results.append(CheckResult("auth_required", "auth_jwt", 0, f"erro: {e}"))

            # rbac_denied: viewer (papel sem permissão) -> 403
            vtoken = _login(base, VIEWER_USER, VIEWER_PASSWORD)
            rbac_note = 0
            rbac_detail = "viewer não autenticou (sem 2º papel?)"
            if vtoken:
                try:
                    r = httpx.post(f"{base}{path}", json=payload,
                                   headers={"Authorization": f"Bearer {vtoken}"}, timeout=5)
                    rbac_note = 100 if r.status_code == 403 else 0
                    rbac_detail = f"viewer em {path} -> {r.status_code} (esperado 403)"
                except httpx.HTTPError as e:
                    rbac_detail = f"erro: {e}"
            results.append(CheckResult("rbac_denied", "rbac", rbac_note, detail=rbac_detail))
        else:
            results.append(CheckResult("auth_required", "auth_jwt", 0,
                                       "nenhuma rota protegida encontrada"))
            results.append(CheckResult("rbac_denied", "rbac", 0,
                                       "nenhuma rota protegida p/ testar RBAC"))

        # api_dashboard: endpoint REST responde
        dash_note = 0
        dash_detail = "GET /api/dashboard não respondeu"
        for path in ("/api/dashboard", "/api/metrics", "/api/assets"):
            try:
                r = httpx.get(f"{base}{path}", timeout=5)
                if r.status_code == 200:
                    dash_note = 100
                    dash_detail = f"GET {path} -> 200"
                    break
            except httpx.HTTPError:
                continue
        results.append(CheckResult("api_dashboard", "api_web", dash_note, detail=dash_detail))

        return results, True, boot_time
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def _find_protected_route(base: str, admin_token: str | None) -> tuple[str, dict] | None:
    """Descobre uma rota de escrita protegida. Tenta candidatos comuns; confirma que com token de
    admin NÃO retorna 401 (i.e., a rota existe e aceita admin)."""
    candidates = [
        ("/api/movements", {"asset_tag": "PROBE-1", "action": "allocate"}),
        ("/api/assets", {"asset_tag": "PROBE-1", "asset_type": "notebook"}),
        ("/api/movement", {"asset_tag": "PROBE-1", "action": "allocate"}),
    ]
    if not admin_token:
        return candidates[0]
    headers = {"Authorization": f"Bearer {admin_token}"}
    for path, payload in candidates:
        try:
            r = httpx.post(f"{base}{path}", json=payload, headers=headers, timeout=5)
            if r.status_code != 404:
                return path, payload
        except httpx.HTTPError:
            continue
    return candidates[0]


# ---------------------------------------------------------------------------
# Ingestão / persistência
# ---------------------------------------------------------------------------
def check_dataset_load(app_dir: Path, env: dict, script: str) -> tuple[CheckResult, CheckResult]:
    """Roda `it-assets import` (se existir) e confere que o SQLite foi populado da base."""
    _uv([script, "import"], app_dir, env, timeout=600)
    db_path = Path(env["DB_PATH"])
    rows = _db_rows(db_path)
    if rows == 0:
        # talvez a carga aconteça só no boot do server — o server check populará; tentamos aqui
        # criando o app via import do módulo não é trivial caixa-preta, então marcamos parcial.
        ingest = CheckResult("dataset_load", "ingestao", 0, "SQLite vazio após import")
        persist = CheckResult("db_populated", "persistence", 0, "SQLite sem linhas de dados")
        return ingest, persist
    ingest = CheckResult("dataset_load", "ingestao", 100, f"{rows} linhas carregadas")
    persist = CheckResult("db_populated", "persistence", 100, f"SQLite populado: {rows} linhas")
    return ingest, persist


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------
def run_checks(app_dir: Path, dataset_path: Path, expected: dict) -> dict:
    db_path = app_dir / "_bench_check.db"
    if db_path.exists():
        db_path.unlink()
    env = _env(app_dir, dataset_path, db_path)
    script = _console_script(app_dir)

    results: list[CheckResult] = []
    flags = {"no_boot": False, "load_time_s": None}
    coverage_pct: float | None = None

    # ingestão/persistência (via console script import)
    ingest_res, persist_res = check_dataset_load(app_dir, env, script)
    results.append(ingest_res)
    results.append(persist_res)

    # testes + cobertura
    cov_res, coverage_pct = check_pytest_coverage(app_dir, env)
    results.append(cov_res)

    # produção (ruff/readme)
    results.append(check_ruff(app_dir, env))
    results.append(check_readme(app_dir))

    # server / uvx boot / auth / rbac / web
    try:
        server_results, served, boot_time = _server_checks(app_dir, env, script)
    except Exception as e:  # noqa: BLE001 - nenhuma checagem pode derrubar o harness
        server_results = [
            CheckResult("uvx_boot", "execucao_uvx", 0, f"exceção: {e}"),
            CheckResult("web_login_form", "api_web", 0, f"exceção: {e}"),
            CheckResult("auth_login", "auth_jwt", 0, f"exceção: {e}"),
            CheckResult("auth_required", "auth_jwt", 0, f"exceção: {e}"),
            CheckResult("rbac_denied", "rbac", 0, f"exceção: {e}"),
            CheckResult("api_dashboard", "api_web", 0, f"exceção: {e}"),
        ]
        served, boot_time = False, 0.0
    results.extend(server_results)
    if not served:
        flags["no_boot"] = True
    flags["load_time_s"] = round(boot_time, 2) if served else None

    # se o import não populou mas o boot popula, reavalia persistence/ingestao pelo db do server
    if served and ingest_res.note == 0:
        db_after = app_dir / next(
            (p.name for p in app_dir.glob("*.db") if p.name != db_path.name), "it_assets.db")
        rows = _db_rows(db_after) or _db_rows(db_path)
        if rows > 0:
            for r in results:
                if r.id == "dataset_load":
                    r.note, r.detail = 100, f"{rows} linhas (populado no boot)"
                if r.id == "db_populated":
                    r.note, r.detail = 100, f"SQLite populado no boot: {rows} linhas"

    # production também reflete uvx boot
    results.append(CheckResult("uvx_production", "production",
                               next((r.note for r in results if r.id == "uvx_boot"), 0),
                               detail="espelha boot via uvx (empacotamento uv/uvx)"))

    # resiliência: estado final passa testes + boot sobre a base (possivelmente mutada)?
    tests_ok = cov_res.note >= 60
    boot_ok = served
    resil_note = 100 if (tests_ok and boot_ok) else (50 if (tests_ok or boot_ok) else 0)
    results.append(CheckResult(
        "resiliencia", "resiliencia", resil_note,
        detail=f"testes_ok={tests_ok}, boot_ok={boot_ok} (estado final pós-perturbação)"))

    by_dim: dict[str, list[float]] = {}
    for r in results:
        by_dim.setdefault(r.dimension, []).append(r.note)
    objective_by_dimension = {d: round(sum(v) / len(v), 1) for d, v in by_dim.items()}

    return {
        "checks": [r.__dict__ for r in results],
        "objective_by_dimension": objective_by_dimension,
        "flags": flags,
        "coverage_pct": coverage_pct,
    }
