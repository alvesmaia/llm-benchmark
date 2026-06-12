"""Checagens objetivas determinísticas sobre o projeto gerado (caixa-preta via `uv run`).

Cada checagem retorna 0-100 e é mapeada para uma dimensão da rubrica. As checagens degradam
graciosamente: nunca levantam exceção não tratada — falha vira nota 0 com detalhe.
"""

from __future__ import annotations

import json
import os
import re
import socket
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from benchmark.harness.adapters.base import run_command

# Mapa de checagem -> dimensão da rubrica.
CHECK_DIMENSION = {
    "files_present": "completeness",
    "etl_load": "etl_parsing",
    "expected_queries": "etl_parsing",
    "cli_multi": "interfaces",
    "api_get": "interfaces",
    "api_post_batch": "interfaces",
    "web_form": "interfaces",
    "uvx_run": "interfaces",
    "idempotent": "persistence",
    "has_index": "persistence",
    "pytest": "tests",
    "err_invalid": "error_handling",
    "err_notfound": "error_handling",
    "err_no_dne": "error_handling",
    "ruff_ok": "production",
    "ci_present": "production",
    "readme_quality": "production",
}


@dataclass
class CheckResult:
    id: str
    dimension: str
    note: float
    detail: str = ""
    data: dict = field(default_factory=dict)


def _env(app_dir: Path, dne_path: Path, db_path: Path) -> dict:
    env = dict(os.environ)
    env["DNE_PATH"] = str(dne_path)
    env["DB_PATH"] = str(db_path)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _uv(args: list[str], cwd: Path, env: dict, timeout: int = 600):
    return run_command(["uv", "run", *args], cwd=cwd, env=env, timeout=timeout)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# Normalização de endereços para comparação tolerante.
# ---------------------------------------------------------------------------
def _norm(value: str) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def _norm_cep(cep: str) -> str:
    return re.sub(r"\D", "", str(cep))


def _address_matches(expected: dict, got: dict) -> bool:
    """Compara os campos esperados (subset) com o resultado, de forma tolerante."""
    if not isinstance(got, dict):
        return False
    # achata possíveis variações de nomes de chave
    flat = {k.lower(): v for k, v in got.items()}
    for key, exp_val in expected.items():
        if key == "cep":
            if _norm_cep(flat.get("cep", "")) != _norm_cep(exp_val):
                return False
            continue
        # aceita sinônimos comuns
        candidates = {
            "logradouro": ["logradouro", "street", "log_no"],
            "tipo_logradouro": ["tipo_logradouro", "tipo", "tlo", "tipo_log"],
            "bairro": ["bairro", "neighborhood"],
            "localidade": ["localidade", "cidade", "municipio", "city"],
            "uf": ["uf", "estado", "state"],
        }.get(key, [key])
        got_val = next((flat[c] for c in candidates if c in flat and flat[c] not in (None, "")), "")
        if _norm(got_val) != _norm(exp_val):
            return False
    return True


# ---------------------------------------------------------------------------
# Checagens individuais
# ---------------------------------------------------------------------------
REQUIRED_ARTIFACTS = {
    "pyproject": ["pyproject.toml"],
    "readme": ["README.md", "README.rst", "readme.md"],
    "ruff_config": ["ruff.toml", ".ruff.toml"],  # ou dentro do pyproject (tratado abaixo)
}


def check_files_present(app_dir: Path) -> CheckResult:
    found = {}
    for key, names in REQUIRED_ARTIFACTS.items():
        found[key] = any((app_dir / n).exists() for n in names)
    # ruff pode estar no pyproject
    if not found["ruff_config"] and (app_dir / "pyproject.toml").exists():
        found["ruff_config"] = "ruff" in (app_dir / "pyproject.toml").read_text(
            encoding="utf-8", errors="replace")
    # tem testes?
    found["tests"] = bool(list(app_dir.rglob("test_*.py")) or list(app_dir.rglob("*_test.py")))
    # tem código python de app?
    py_files = [p for p in app_dir.rglob("*.py") if ".venv" not in p.parts]
    found["python_code"] = len(py_files) >= 3
    # CI
    found["ci"] = bool(list((app_dir / ".github" / "workflows").glob("*.y*ml"))) \
        if (app_dir / ".github" / "workflows").exists() else False

    note = 100 * sum(1 for v in found.values() if v) / len(found)
    return CheckResult("files_present", "completeness", round(note, 1),
                       detail=f"{sum(found.values())}/{len(found)} artefatos", data=found)


def check_etl_load(app_dir: Path, env: dict) -> tuple[CheckResult, float]:
    rc, out, err, dur = _uv(["cep-etl", "load"], app_dir, env, timeout=900)
    ok = rc == 0
    detail = "ok" if ok else f"rc={rc}: {(err or out).strip()[-300:]}"
    return CheckResult("etl_load", "etl_parsing", 100 if ok else 0, detail=detail), dur


def check_expected_queries(app_dir: Path, env: dict, expected: dict) -> CheckResult:
    found = expected.get("found", {})
    if not found:
        return CheckResult("expected_queries", "etl_parsing", 0, "sem queries esperadas")
    correct = 0
    misses = []
    for cep, exp in found.items():
        rc, out, _err, _ = _uv(["cep-etl", "query", cep, "--json"], app_dir, env, timeout=120)
        ok = False
        if rc == 0 and out.strip():
            try:
                blob = out.strip()
                parsed = json.loads(blob.splitlines()[-1] if "\n" in blob else blob)
                # resultado pode ser objeto único ou lista
                candidates = parsed if isinstance(parsed, list) else [parsed]
                ok = any(_address_matches(exp, c) for c in candidates)
            except (json.JSONDecodeError, IndexError):
                ok = False
        correct += int(ok)
        if not ok:
            misses.append(cep)
    note = 100 * correct / len(found)
    return CheckResult("expected_queries", "etl_parsing", round(note, 1),
                       detail=f"{correct}/{len(found)} corretos; erros: {misses}")


def check_cli_multi(app_dir: Path, env: dict, expected: dict) -> CheckResult:
    ceps = [c for c in expected.get("found", {}) if "-" not in c][:2]
    if len(ceps) < 2:
        ceps = ["01001000", "20040002"]
    rc, out, _err, _ = _uv(["cep-etl", "query", *ceps, "--json"], app_dir, env, timeout=120)
    ok = rc == 0 and out.strip().count("cep") >= 2 if out else False
    return CheckResult("cli_multi", "interfaces", 100 if ok else 0,
                       detail="aceita 2+ CEPs" if ok else "não retornou múltiplos")


def check_error_handling(app_dir: Path, env: dict, expected: dict) -> list[CheckResult]:
    results = []

    # CEP inválido: deve sair com erro tratado (rc!=0 OU mensagem) sem traceback cru
    invalid = (expected.get("invalid") or ["abc"])[0]
    rc, out, err, _ = _uv(["cep-etl", "query", invalid, "--json"], app_dir, env, timeout=120)
    blob = (out + err)
    has_traceback = "Traceback (most recent call last)" in blob
    handled = (not has_traceback) and (rc != 0 or "inv" in blob.lower() or "erro" in blob.lower()
                                       or "invalid" in blob.lower())
    results.append(CheckResult("err_invalid", "error_handling", 100 if handled else 0,
                               detail="tratado" if handled else "stack trace cru / não tratado"))

    # CEP não encontrado: não pode quebrar (sem traceback)
    nf = (expected.get("not_found") or ["99999999"])[0]
    rc, out, err, _ = _uv(["cep-etl", "query", nf, "--json"], app_dir, env, timeout=120)
    blob = out + err
    handled_nf = "Traceback (most recent call last)" not in blob
    results.append(CheckResult("err_notfound", "error_handling", 100 if handled_nf else 0,
                               detail="tratado" if handled_nf else "quebrou em CEP inexistente"))

    # DNE ausente: load apontando para pasta vazia deve dar mensagem acionável
    empty = app_dir / "_empty_dne_probe"
    empty.mkdir(exist_ok=True)
    env2 = dict(env)
    env2["DNE_PATH"] = str(empty)
    env2["DB_PATH"] = str(app_dir / "_probe.db")
    rc, out, err, _ = _uv(["cep-etl", "load"], app_dir, env2, timeout=120)
    blob = out + err
    handled_dne = "Traceback (most recent call last)" not in blob and rc != 0
    results.append(CheckResult("err_no_dne", "error_handling", 100 if handled_dne else 0,
                               detail="mensagem acionável" if handled_dne else "não tratado"))
    return results


def _count_db_rows(db_path: Path) -> int | None:
    if not db_path.exists():
        return None
    try:
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        tables = [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        total = 0
        for t in tables:
            total += cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        con.close()
        return total
    except sqlite3.Error:
        return None


def check_idempotent(app_dir: Path, env: dict) -> CheckResult:
    db_path = Path(env["DB_PATH"])
    before = _count_db_rows(db_path)
    if before is None:
        return CheckResult("idempotent", "persistence", 0, "banco SQLite não encontrado p/ checar")
    _uv(["cep-etl", "load"], app_dir, env, timeout=900)
    after = _count_db_rows(db_path)
    ok = after is not None and after == before
    return CheckResult("idempotent", "persistence", 100 if ok else 0,
                       detail=f"linhas antes={before} depois={after}")


def check_has_index(env: dict) -> CheckResult:
    db_path = Path(env["DB_PATH"])
    if not db_path.exists():
        return CheckResult("has_index", "persistence", 0, "sem banco SQLite")
    try:
        con = sqlite3.connect(str(db_path))
        idx = con.execute(
            "SELECT sql FROM sqlite_master WHERE type='index'").fetchall()
        # índice explícito mencionando cep, OU coluna cep como PK/unique
        has = any(row[0] and "cep" in row[0].lower() for row in idx if row[0])
        if not has:
            # checa se alguma tabela tem coluna cep indexada por PK/unique
            for (sql,) in con.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table'").fetchall():
                if sql and re.search(r"cep[^,]*\b(primary key|unique)", sql, re.IGNORECASE):
                    has = True
                    break
        con.close()
        return CheckResult("has_index", "persistence", 100 if has else 0,
                           detail="índice/uniqueness por CEP" if has else "sem índice por CEP")
    except sqlite3.Error as e:
        return CheckResult("has_index", "persistence", 0, f"erro sqlite: {e}")


def check_pytest(app_dir: Path, env: dict) -> CheckResult:
    rc, out, err, _ = _uv(["pytest", "-q"], app_dir, env, timeout=900)
    blob = out + err
    m = re.search(r"(\d+) passed", blob)
    f = re.search(r"(\d+) failed", blob)
    passed = int(m.group(1)) if m else 0
    failed = int(f.group(1)) if f else 0
    total = passed + failed
    if total == 0:
        note = 0 if rc != 0 else 50  # rodou mas sem testes detectados
        return CheckResult("pytest", "tests", note, detail=f"rc={rc}, sem contagem de testes")
    note = 100 * passed / total
    return CheckResult("pytest", "tests", round(note, 1),
                       detail=f"{passed} passed / {failed} failed")


def check_uvx_run(app_dir: Path, env: dict) -> CheckResult:
    rc, out, err, _ = run_command(["uvx", "--from", str(app_dir), "cep-etl", "--help"],
                                  cwd=app_dir, env=env, timeout=600)
    ok = rc == 0
    return CheckResult("uvx_run", "interfaces", 100 if ok else 0,
                       detail="uvx executa" if ok else f"rc={rc}: {(err or out)[-200:]}")


def check_ruff(app_dir: Path, env: dict) -> CheckResult:
    rc, out, err, _ = _uv(["ruff", "check", "."], app_dir, env, timeout=300)
    if rc == 0:
        return CheckResult("ruff_ok", "production", 100, "sem erros de lint")
    blob = out + err
    n = len(re.findall(r"^\S+:\d+:\d+", blob, re.MULTILINE))
    note = 50 if n and n <= 10 else 20
    return CheckResult("ruff_ok", "production", note, detail=f"{n} achados de lint")


def check_ci_present(app_dir: Path) -> CheckResult:
    wf = app_dir / ".github" / "workflows"
    files = list(wf.glob("*.y*ml")) if wf.exists() else []
    if not files:
        return CheckResult("ci_present", "production", 0, "sem workflow de CI")
    txt = " ".join(p.read_text(encoding="utf-8", errors="replace") for p in files).lower()
    runs_tests = ("pytest" in txt or "test" in txt) and ("ruff" in txt or "lint" in txt)
    return CheckResult("ci_present", "production", 100 if runs_tests else 60,
                       detail="CI roda lint+testes" if runs_tests else "CI presente (parcial)")


def check_readme(app_dir: Path) -> CheckResult:
    for name in ("README.md", "readme.md", "README.rst"):
        p = app_dir / name
        if p.exists():
            txt = p.read_text(encoding="utf-8", errors="replace").lower()
            has_load = "load" in txt or "etl" in txt or "carga" in txt
            has_usage = "query" in txt or "uso" in txt or "usage" in txt or "serve" in txt
            note = 100 if (has_load and has_usage) else (60 if (has_load or has_usage) else 30)
            return CheckResult("readme_quality", "production", note,
                               detail=f"load={has_load}, uso={has_usage}")
    return CheckResult("readme_quality", "production", 0, "sem README")


# ---------------------------------------------------------------------------
# Checagens que precisam do servidor no ar
# ---------------------------------------------------------------------------
def _server_checks(app_dir: Path, env: dict, expected: dict) -> list[CheckResult]:
    port = _free_port()
    env = dict(env)
    proc = subprocess.Popen(
        ["uv", "run", "cep-etl", "serve", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(app_dir), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base_candidates = [f"http://127.0.0.1:{port}", "http://127.0.0.1:8000"]
    base = None
    deadline = time.monotonic() + 40
    try:
        while time.monotonic() < deadline and base is None:
            for b in base_candidates:
                try:
                    # qualquer resposta HTTP (mesmo 500) significa que o servidor está no ar
                    httpx.get(b + "/", timeout=2)
                    base = b
                    break
                except httpx.HTTPError:
                    continue
            if base is None:
                time.sleep(1)

        if base is None:
            return [
                CheckResult("web_form", "interfaces", 0, "servidor não respondeu"),
                CheckResult("api_get", "interfaces", 0, "servidor não respondeu"),
                CheckResult("api_post_batch", "interfaces", 0, "servidor não respondeu"),
            ], False  # noqa: B901 (tratado pelo chamador via tuple)

        results = []
        # web_form
        try:
            r = httpx.get(base + "/", timeout=5)
            html = r.text.lower()
            ok = r.status_code == 200 and "<form" in html
            results.append(CheckResult("web_form", "interfaces", 100 if ok else 0,
                                       detail="formulário presente" if ok else "sem <form>"))
        except httpx.HTTPError as e:
            results.append(CheckResult("web_form", "interfaces", 0, f"erro: {e}"))

        # api_get
        found = expected.get("found", {})
        sample = next((c for c in found if "-" not in c), "01001000")
        try:
            r = httpx.get(f"{base}/cep/{sample}", timeout=5)
            ok = r.status_code == 200 and _address_matches(found.get(sample, {}), r.json())
            results.append(CheckResult("api_get", "interfaces", 100 if ok else 0,
                                       detail=f"GET /cep/{sample} -> {r.status_code}"))
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            results.append(CheckResult("api_get", "interfaces", 0, f"erro: {e}"))

        # api_post_batch
        ceps = [c for c in found if "-" not in c][:2] or ["01001000", "20040002"]
        try:
            r = httpx.post(f"{base}/ceps", json={"ceps": ceps}, timeout=5)
            body = r.json()
            count = len(body) if isinstance(body, list) else len(body.get("results", body)) \
                if isinstance(body, dict) else 0
            ok = r.status_code == 200 and count >= len(ceps)
            results.append(CheckResult("api_post_batch", "interfaces", 100 if ok else 0,
                                       detail=f"POST /ceps -> {r.status_code}, {count} itens"))
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            results.append(CheckResult("api_post_batch", "interfaces", 0, f"erro: {e}"))

        return results, True
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def run_all_checks(app_dir: Path, dne_path: Path, expected: dict) -> dict:
    """Roda todas as checagens objetivas e agrega por dimensão + flags de modificadores."""
    db_path = app_dir / "_bench_check.db"
    if db_path.exists():
        db_path.unlink()
    env = _env(app_dir, dne_path, db_path)

    results: list[CheckResult] = []
    flags = {"no_boot": False, "load_time_s": None}

    results.append(check_files_present(app_dir))

    load_res, load_dur = check_etl_load(app_dir, env)
    results.append(load_res)
    flags["load_time_s"] = round(load_dur, 2)

    results.append(check_expected_queries(app_dir, env, expected))
    results.append(check_cli_multi(app_dir, env, expected))
    results.append(check_uvx_run(app_dir, env))
    results.append(check_idempotent(app_dir, env))
    results.append(check_has_index(env))
    results.append(check_pytest(app_dir, env))
    results.extend(check_error_handling(app_dir, env, expected))
    results.append(check_ruff(app_dir, env))
    results.append(check_ci_present(app_dir))
    results.append(check_readme(app_dir))

    # server checks
    try:
        server_results, served = _server_checks(app_dir, env, expected)
    except Exception as e:  # noqa: BLE001 - robustez: nenhuma checagem pode derrubar o harness
        server_results = [
            CheckResult("web_form", "interfaces", 0, f"exceção: {e}"),
            CheckResult("api_get", "interfaces", 0, f"exceção: {e}"),
            CheckResult("api_post_batch", "interfaces", 0, f"exceção: {e}"),
        ]
        served = False
    results.extend(server_results)
    if not served:
        flags["no_boot"] = True

    # agrega por dimensão (média das checagens objetivas daquela dimensão)
    by_dim: dict[str, list[float]] = {}
    for r in results:
        by_dim.setdefault(r.dimension, []).append(r.note)
    objective_by_dimension = {d: round(sum(v) / len(v), 1) for d, v in by_dim.items()}

    return {
        "checks": [r.__dict__ for r in results],
        "objective_by_dimension": objective_by_dimension,
        "flags": flags,
    }
