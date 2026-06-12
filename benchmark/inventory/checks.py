"""Checagens objetivas do cenário `inventory` (caixa-preta via `uv run` / HTTP).

Reaproveita helpers do checks do CEP (`_uv`, `_free_port`, `check_pytest`, `check_ruff`,
`check_ci_present`, `check_readme`, `CheckResult`). Cada checagem retorna 0-100 e é mapeada para
uma dimensão da rubrica do inventory. Falhas degradam para 0 com detalhe — nunca derrubam o harness.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
from pathlib import Path

import httpx

from benchmark.harness.adapters.base import run_command
from benchmark.harness.checks import (
    CheckResult,
    _free_port,
    _uv,
    check_ci_present,
    check_pytest,
    check_readme,
    check_ruff,
)

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def _env(app_dir: Path, dataset_path: Path, db_path: Path) -> dict:
    env = dict(os.environ)
    env["DATASET_PATH"] = str(dataset_path)
    env["DB_PATH"] = str(db_path)
    env["ADMIN_USER"] = ADMIN_USER
    env["ADMIN_PASSWORD"] = ADMIN_PASSWORD
    env["PYTHONIOENCODING"] = "utf-8"
    return env


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _table_names(con: sqlite3.Connection) -> list[str]:
    return [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]


def _find_table(con: sqlite3.Connection, needles: list[str]) -> str | None:
    for name in _table_names(con):
        low = name.lower()
        if any(n in low for n in needles):
            return name
    return None


def _count(con: sqlite3.Connection, table: str) -> int:
    try:
        return con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    except sqlite3.Error:
        return 0


# ---------------------------------------------------------------------------
# Ingestão (import)
# ---------------------------------------------------------------------------
def check_dataset_load(app_dir: Path, env: dict) -> tuple[CheckResult, float]:
    rc, out, err, dur = _uv(["inv-etl", "import"], app_dir, env, timeout=600)
    db_path = Path(env["DB_PATH"])
    note = 0
    detail = f"rc={rc}: {(err or out).strip()[-200:]}"
    if rc == 0 and db_path.exists():
        try:
            con = sqlite3.connect(str(db_path))
            prod_t = _find_table(con, ["product", "produto"])
            mov_t = _find_table(con, ["movement", "moviment", "mov"])
            n_prod = _count(con, prod_t) if prod_t else 0
            n_mov = _count(con, mov_t) if mov_t else 0
            con.close()
            ok = n_prod >= 1 and n_mov >= 1
            note = 100 if ok else (50 if (n_prod or n_mov) else 0)
            detail = f"produtos={n_prod}, movimentações={n_mov}"
        except sqlite3.Error as e:
            detail = f"erro sqlite: {e}"
    return CheckResult("dataset_load", "ingestao", note, detail=detail), dur


def check_idempotent(app_dir: Path, env: dict) -> CheckResult:
    db_path = Path(env["DB_PATH"])
    if not db_path.exists():
        return CheckResult("idempotent", "persistence", 0, "sem banco para checar idempotência")
    try:
        con = sqlite3.connect(str(db_path))
        mov_t = _find_table(con, ["movement", "moviment", "mov"])
        before = _count(con, mov_t) if mov_t else 0
        con.close()
    except sqlite3.Error as e:
        return CheckResult("idempotent", "persistence", 0, f"erro sqlite: {e}")
    _uv(["inv-etl", "import"], app_dir, env, timeout=600)
    try:
        con = sqlite3.connect(str(db_path))
        mov_t = _find_table(con, ["movement", "moviment", "mov"])
        after = _count(con, mov_t) if mov_t else 0
        con.close()
    except sqlite3.Error as e:
        return CheckResult("idempotent", "persistence", 0, f"erro sqlite: {e}")
    ok = before > 0 and after == before
    return CheckResult("idempotent", "persistence", 100 if ok else 0,
                       detail=f"movimentações antes={before} depois={after}")


def check_has_index(env: dict) -> CheckResult:
    db_path = Path(env["DB_PATH"])
    if not db_path.exists():
        return CheckResult("has_index", "persistence", 0, "sem banco SQLite")
    try:
        con = sqlite3.connect(str(db_path))
        idx = con.execute("SELECT sql FROM sqlite_master WHERE type='index'").fetchall()
        has = any(row[0] and ("product" in row[0].lower() or "company" in row[0].lower()
                              or "model" in row[0].lower() or "movement" in row[0].lower())
                  for row in idx if row[0])
        if not has:
            for (sql,) in con.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table'").fetchall():
                if sql and ("unique" in sql.lower() or "primary key" in sql.lower()):
                    has = True
                    break
        con.close()
        return CheckResult("has_index", "persistence", 100 if has else 0,
                           detail="índice/uniqueness presente" if has else "sem índice")
    except sqlite3.Error as e:
        return CheckResult("has_index", "persistence", 0, f"erro sqlite: {e}")


def check_password_hashed(env: dict, app_dir: Path) -> CheckResult:
    """Inspeciona a tabela de usuários e confere que a senha não está em texto plano."""
    # garante o seed do admin: o boot do server cria; tentamos um login via DB direto se já existe.
    db_path = Path(env["DB_PATH"])
    if not db_path.exists():
        return CheckResult("password_hashed", "auth", 0, "sem banco para inspecionar usuários")
    try:
        con = sqlite3.connect(str(db_path))
        user_t = _find_table(con, ["user", "usuario", "account", "auth"])
        if not user_t:
            con.close()
            return CheckResult("password_hashed", "auth", 0, "tabela de usuários não encontrada")
        cur = con.execute(f'SELECT * FROM "{user_t}" LIMIT 5')
        cols = [d[0].lower() for d in cur.description]
        rows = cur.fetchall()
        con.close()
        if not rows:
            return CheckResult("password_hashed", "auth", 0, "sem usuários semeados")
        plain = ADMIN_PASSWORD.lower()
        leaked = False
        for row in rows:
            for col, val in zip(cols, row, strict=False):
                if isinstance(val, str) and "pass" in col and val.lower() == plain:
                    leaked = True
        note = 0 if leaked else 100
        return CheckResult("password_hashed", "auth", note,
                           detail="senha em hash" if not leaked else "senha em TEXTO PLANO")
    except sqlite3.Error as e:
        return CheckResult("password_hashed", "auth", 0, f"erro sqlite: {e}")


# ---------------------------------------------------------------------------
# Server / HTTP checks
# ---------------------------------------------------------------------------
def _login(base: str) -> str | None:
    try:
        r = httpx.post(f"{base}/auth/login",
                       json={"username": ADMIN_USER, "password": ADMIN_PASSWORD}, timeout=5)
        if r.status_code == 200:
            body = r.json()
            for key in ("token", "access_token", "jwt"):
                if isinstance(body, dict) and body.get(key):
                    return str(body[key])
    except (httpx.HTTPError, json.JSONDecodeError):
        return None
    return None


def _server_checks(app_dir: Path, env: dict, expected: dict) -> tuple[list[CheckResult], bool]:
    port = _free_port()
    proc = subprocess.Popen(
        ["uv", "run", "inv-etl", "serve", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(app_dir), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = None
    deadline = time.monotonic() + 40
    try:
        while time.monotonic() < deadline and base is None:
            try:
                httpx.get(f"http://127.0.0.1:{port}/", timeout=2)
                base = f"http://127.0.0.1:{port}"
            except httpx.HTTPError:
                time.sleep(1)

        names = ["web_form", "auth_login", "auth_required", "crud_product",
                 "stock_in_out", "dashboard_endpoint", "expected_metrics"]
        dims = {"web_form": "auth", "auth_login": "auth", "auth_required": "auth",
                "crud_product": "inventory_logic", "stock_in_out": "inventory_logic",
                "dashboard_endpoint": "dashboard", "expected_metrics": "dashboard"}
        if base is None:
            return [CheckResult(n, dims[n], 0, "servidor não respondeu") for n in names], False

        results: list[CheckResult] = []

        # snapshot LIMPO do dashboard (antes de qualquer mutação dos checks de estoque), para
        # comparar com expected_metrics.json sem poluição das movimentações de teste.
        clean_dash = None
        try:
            rd = httpx.get(f"{base}/api/dashboard", timeout=5)
            if rd.status_code == 200:
                clean_dash = rd.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            clean_dash = None

        # web_form
        try:
            r = httpx.get(base + "/", timeout=5)
            html = r.text.lower()
            ok = r.status_code == 200 and "<form" in html \
                and "username" in html and "password" in html
            results.append(CheckResult("web_form", "auth", 100 if ok else 0,
                                       detail="form de login presente" if ok else "form ausente"))
        except httpx.HTTPError as e:
            results.append(CheckResult("web_form", "auth", 0, f"erro: {e}"))

        # auth_login (válido vs inválido)
        token = _login(base)
        bad_status = None
        try:
            rb = httpx.post(f"{base}/auth/login",
                            json={"username": ADMIN_USER, "password": "senha_errada_xyz"},
                            timeout=5)
            bad_status = rb.status_code
        except httpx.HTTPError:
            bad_status = None
        login_ok = token is not None and bad_status == 401
        results.append(CheckResult("auth_login", "auth", 100 if login_ok else 0,
                                   detail=f"login válido={'ok' if token else 'falhou'}, "
                                          f"inválido->{bad_status}"))

        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # auth_required: POST protegido SEM token -> 401/403
        try:
            r = httpx.post(f"{base}/api/products",
                           json={"company": "ZZ", "model": "Probe", "unit_cost": 1}, timeout=5)
            ok = r.status_code in (401, 403)
            results.append(CheckResult("auth_required", "auth", 100 if ok else 0,
                                       detail=f"POST sem token -> {r.status_code}"))
        except httpx.HTTPError as e:
            results.append(CheckResult("auth_required", "auth", 0, f"erro: {e}"))

        # crud_product: POST autenticado + GET lista contém
        crud_ok = False
        pid = None
        if token:
            try:
                r = httpx.post(f"{base}/api/products",
                               json={"company": "TestCo", "model": "ProbeModel", "unit_cost": 10},
                               headers=headers, timeout=5)
                if r.status_code in (200, 201):
                    body = r.json()
                    pid = body.get("id") if isinstance(body, dict) else None
                    lst = httpx.get(f"{base}/api/products", timeout=5).json()
                    crud_ok = any(
                        isinstance(p, dict)
                        and str(p.get("company", "")).lower() == "testco"
                        and str(p.get("model", "")).lower() == "probemodel"
                        for p in (lst if isinstance(lst, list) else []))
            except (httpx.HTTPError, json.JSONDecodeError):
                crud_ok = False
        results.append(CheckResult("crud_product", "inventory_logic", 100 if crud_ok else 0,
                                   detail=f"produto criado e listado (id={pid})" if crud_ok
                                   else "CRUD de produto falhou"))

        # stock_in_out: in qty=10, out qty=3 -> stock 7; out qty=100 -> 400
        stock_note = 0
        stock_detail = "sem produto/token para testar estoque"
        if token and pid is not None:
            try:
                httpx.post(f"{base}/api/movements",
                           json={"product_id": pid, "type": "in", "qty": 10},
                           headers=headers, timeout=5)
                httpx.post(f"{base}/api/movements",
                           json={"product_id": pid, "type": "out", "qty": 3},
                           headers=headers, timeout=5)
                lst = httpx.get(f"{base}/api/products", timeout=5).json()
                cur = next((p for p in lst if isinstance(p, dict) and p.get("id") == pid), {})
                stock = cur.get("stock")
                over = httpx.post(f"{base}/api/movements",
                                  json={"product_id": pid, "type": "out", "qty": 100},
                                  headers=headers, timeout=5)
                stock_ok = stock == 7
                over_ok = over.status_code == 400
                stock_note = 100 if (stock_ok and over_ok) else (50 if (stock_ok or over_ok) else 0)
                stock_detail = f"stock após in10/out3 = {stock} (esperado 7); " \
                               f"out100 -> {over.status_code} (esperado 400)"
            except (httpx.HTTPError, json.JSONDecodeError) as e:
                stock_detail = f"erro: {e}"
        results.append(CheckResult("stock_in_out", "inventory_logic", stock_note,
                                   detail=stock_detail))

        # dashboard_endpoint: existe e tem as chaves
        dash = None
        try:
            r = httpx.get(f"{base}/api/dashboard", timeout=5)
            if r.status_code == 200:
                dash = r.json()
            keys = {"revenue", "cost", "profit", "units_sold", "movements",
                    "by_company", "by_region"}
            present = isinstance(dash, dict) and keys.issubset(set(dash))
            results.append(CheckResult("dashboard_endpoint", "dashboard", 100 if present else 0,
                                       detail=f"GET /api/dashboard -> {r.status_code}, "
                                              f"chaves={'ok' if present else 'faltando'}"))
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            results.append(CheckResult("dashboard_endpoint", "dashboard", 0, f"erro: {e}"))

        # expected_metrics: compara o snapshot LIMPO com expected_metrics.json (tolerância)
        results.append(_check_expected_metrics(clean_dash, expected))

        return results, True
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def _approx(a, b, tol: float = 0.02) -> bool:
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    if b == 0:
        return abs(a) <= 1
    return abs(a - b) / abs(b) <= tol


def _check_expected_metrics(dash: dict | None, expected: dict) -> CheckResult:
    if not isinstance(dash, dict):
        return CheckResult("expected_metrics", "dashboard", 0, "dashboard indisponível")
    checks = []
    checks.append(_approx(dash.get("revenue"), expected.get("revenue")))
    checks.append(_approx(dash.get("units_sold"), expected.get("units_sold")))

    def _map_match(got, exp) -> bool:
        if not isinstance(got, dict) or not isinstance(exp, dict):
            return False
        hits = sum(1 for k, v in exp.items() if _approx(got.get(k), v))
        return hits >= max(1, int(0.7 * len(exp)))

    checks.append(_map_match(dash.get("by_company"), expected.get("by_company", {})))
    checks.append(_map_match(dash.get("by_region"), expected.get("by_region", {})))

    note = round(100 * sum(checks) / len(checks), 1)
    detail = (f"revenue={dash.get('revenue')}/{expected.get('revenue')}, "
              f"units={dash.get('units_sold')}/{expected.get('units_sold')}, "
              f"by_company={'ok' if checks[2] else 'x'}, by_region={'ok' if checks[3] else 'x'}")
    return CheckResult("expected_metrics", "dashboard", note, detail=detail)


# ---------------------------------------------------------------------------
# Produção / API (reaproveitando helpers)
# ---------------------------------------------------------------------------
def check_uvx_run(app_dir: Path, env: dict) -> CheckResult:
    rc, out, err, _ = run_command(["uvx", "--from", str(app_dir), "inv-etl", "--help"],
                                  cwd=app_dir, env=env, timeout=600)
    ok = rc == 0
    return CheckResult("uvx_run", "api_rest", 100 if ok else 0,
                       detail="uvx executa" if ok else f"rc={rc}: {(err or out)[-200:]}")


def check_files_present(app_dir: Path) -> CheckResult:
    found = {
        "pyproject": (app_dir / "pyproject.toml").exists(),
        "readme": any((app_dir / n).exists() for n in ("README.md", "readme.md", "README.rst")),
    }
    found["ruff_config"] = (app_dir / "ruff.toml").exists() or (
        (app_dir / "pyproject.toml").exists()
        and "ruff" in (app_dir / "pyproject.toml").read_text(encoding="utf-8", errors="replace"))
    found["tests"] = bool(list(app_dir.rglob("test_*.py")) or list(app_dir.rglob("*_test.py")))
    py_files = [p for p in app_dir.rglob("*.py") if ".venv" not in p.parts]
    found["python_code"] = len(py_files) >= 3
    found["ci"] = bool(list((app_dir / ".github" / "workflows").glob("*.y*ml"))) \
        if (app_dir / ".github" / "workflows").exists() else False
    note = 100 * sum(1 for v in found.values() if v) / len(found)
    return CheckResult("files_present", "production", round(note, 1),
                       detail=f"{sum(found.values())}/{len(found)} artefatos", data=found)


# ---------------------------------------------------------------------------
# Tratamento de erros
# ---------------------------------------------------------------------------
def check_error_handling(app_dir: Path, env: dict) -> CheckResult:
    """import com DATASET_PATH ausente deve dar mensagem acionável (rc!=0, sem traceback cru)."""
    env2 = dict(env)
    env2["DATASET_PATH"] = str(app_dir / "_nao_existe_probe.csv")
    env2["DB_PATH"] = str(app_dir / "_probe.db")
    rc, out, err, _ = _uv(["inv-etl", "import"], app_dir, env2, timeout=120)
    blob = out + err
    handled = "Traceback (most recent call last)" not in blob and rc != 0
    return CheckResult("err_missing_dataset", "error_handling", 100 if handled else 0,
                       detail="mensagem acionável" if handled else "não tratado / traceback cru")


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------
def run_checks(app_dir: Path, dataset_path: Path, expected: dict) -> dict:
    db_path = app_dir / "_bench_check.db"
    if db_path.exists():
        db_path.unlink()
    env = _env(app_dir, dataset_path, db_path)

    results: list[CheckResult] = []
    flags = {"no_boot": False, "load_time_s": None}

    results.append(check_files_present(app_dir))

    load_res, load_dur = check_dataset_load(app_dir, env)
    results.append(load_res)
    flags["load_time_s"] = round(load_dur, 2)

    results.append(check_idempotent(app_dir, env))
    results.append(check_has_index(env))
    results.append(check_pytest(app_dir, env))
    results.append(check_uvx_run(app_dir, env))
    results.append(check_error_handling(app_dir, env))
    results.append(check_ruff(app_dir, env))
    results.append(check_ci_present(app_dir))
    results.append(check_readme(app_dir))

    # server checks (precisam do banco já populado)
    try:
        server_results, served = _server_checks(app_dir, env, expected)
    except Exception as e:  # noqa: BLE001 - nenhuma checagem pode derrubar o harness
        server_results = [
            CheckResult("web_form", "auth", 0, f"exceção: {e}"),
            CheckResult("auth_login", "auth", 0, f"exceção: {e}"),
            CheckResult("auth_required", "auth", 0, f"exceção: {e}"),
            CheckResult("crud_product", "inventory_logic", 0, f"exceção: {e}"),
            CheckResult("stock_in_out", "inventory_logic", 0, f"exceção: {e}"),
            CheckResult("dashboard_endpoint", "dashboard", 0, f"exceção: {e}"),
            CheckResult("expected_metrics", "dashboard", 0, f"exceção: {e}"),
        ]
        served = False
    results.extend(server_results)
    if not served:
        flags["no_boot"] = True

    # password_hashed depende do banco semeado pelo boot do server.
    results.append(check_password_hashed(env, app_dir))

    # checagens que mapeiam para api_rest além do uvx: reaproveita ruff/readme já feitos.
    # crud_product e dashboard_endpoint também informam api_rest indiretamente via cópias:
    results.append(CheckResult(
        "api_products_list", "api_rest",
        next((r.note for r in results if r.id == "crud_product"), 0),
        detail="espelha crud_product (lista de produtos via API)"))
    results.append(CheckResult(
        "api_dashboard", "api_rest",
        next((r.note for r in results if r.id == "dashboard_endpoint"), 0),
        detail="espelha dashboard_endpoint (endpoint REST)"))

    by_dim: dict[str, list[float]] = {}
    for r in results:
        by_dim.setdefault(r.dimension, []).append(r.note)
    objective_by_dimension = {d: round(sum(v) / len(v), 1) for d, v in by_dim.items()}

    return {
        "checks": [r.__dict__ for r in results],
        "objective_by_dimension": objective_by_dimension,
        "flags": flags,
    }
