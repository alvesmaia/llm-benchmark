"""Orquestrador: executa a matriz de candidatos em 3 fases, coleta artefatos e pontua."""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from benchmark.harness import gitcheck, gitsetup
from benchmark.harness import judge as judge_mod
from benchmark.harness import score as score_mod
from benchmark.harness.adapters.base import get_adapter
from benchmark.harness.config import Candidate, Config
from benchmark.harness.scenarios.registry import get_scenario


def _load_expected(cfg: Config, scenario) -> dict:
    return json.loads(cfg.expected_for(scenario.id).read_text(encoding="utf-8"))


def _phase_prompt(scenario, name: str) -> str:
    return (scenario.brief_dir / f"{name}.md").read_text(encoding="utf-8")


def _build_phase1_prompt(scenario) -> str:
    p1 = _phase_prompt(scenario, "phase1_prompt")
    challenge = (scenario.brief_dir / "challenge.md").read_text(encoding="utf-8")
    return f"{p1}\n\n{challenge}"


def _agent_env(cfg: Config, app_dir: Path, scenario) -> dict:
    env = dict(os.environ)
    env[scenario.dataset_env] = str(cfg.dataset_for(scenario.id))
    env["DB_PATH"] = str(app_dir / scenario.db_filename)
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(scenario.extra_env)
    return env


def run_candidate(cfg: Config, candidate: Candidate, scenario=None, *,
                  skip_agent: bool = False) -> dict:
    """Executa um candidato de ponta a ponta. Se skip_agent, assume que app/ já existe."""
    scenario = scenario or get_scenario("cep_etl")
    slug = candidate.slug
    run_dir = scenario.run_dir(cfg.runs_dir, slug)
    app_dir = run_dir / "app"
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    app_dir.mkdir(parents=True, exist_ok=True)

    started = datetime.now(UTC).isoformat()
    phases = {}

    if not skip_agent:
        git_info = gitsetup.init_nested_repo(app_dir, slug, cfg.git)
        (logs_dir / "gitsetup.json").write_text(json.dumps(git_info, indent=2), encoding="utf-8")

        adapter = get_adapter(candidate.agent, candidate.model, effort=candidate.effort)
        env = _agent_env(cfg, app_dir, scenario)

        p1 = adapter.build(_build_phase1_prompt(scenario), app_dir, env)
        phases["phase1"] = p1.to_dict()
        (logs_dir / "phase1.json").write_text(json.dumps(p1.to_dict(), indent=2), encoding="utf-8")

        p2 = adapter.continue_session("phase2", _phase_prompt(scenario, "phase2_prompt"),
                                      app_dir, env, p1)
        phases["phase2"] = p2.to_dict()
        (logs_dir / "phase2.json").write_text(json.dumps(p2.to_dict(), indent=2), encoding="utf-8")

        p3 = adapter.continue_session("phase3", _phase_prompt(scenario, "phase3_prompt"),
                                      app_dir, env, p2)
        phases["phase3"] = p3.to_dict()
        (logs_dir / "phase3.json").write_text(json.dumps(p3.to_dict(), indent=2), encoding="utf-8")

        push_res = gitsetup.push_results(app_dir, slug, cfg.git)
        (logs_dir / "push.json").write_text(json.dumps(push_res, indent=2), encoding="utf-8")

    # ----- avaliação -----
    expected = _load_expected(cfg, scenario)
    objective = scenario.run_checks(app_dir, cfg.dataset_for(scenario.id), expected)

    git_res = gitcheck.check_git(app_dir, slug, cfg.git)
    # injeta a nota de git como dimensão objetiva
    objective["objective_by_dimension"]["git"] = git_res["note"]
    objective["git_detail"] = git_res

    panel = judge_mod.run_panel(app_dir, slug, objective, cfg, scenario)
    if panel.get("hallucinated_dependency_votes"):
        objective["flags"]["hallucinated_dependency"] = True
    # persiste o prompt do juiz (idêntico p/ todos) p/ reuso/export e juiz externo
    (logs_dir / "judge_prompt.md").write_text(panel.get("prompt", ""), encoding="utf-8")

    scored = score_mod.compute_score(
        objective["objective_by_dimension"], panel["averaged_by_dimension"],
        objective["flags"], cfg, scenario,
    )

    result = {
        "slug": slug,
        "agent": candidate.agent,
        "model": candidate.model,
        "scenario": scenario.id,
        "started_utc": started,
        "finished_utc": datetime.now(UTC).isoformat(),
        "phases": phases,
        "score": scored,
        "divergences": panel["divergences"],
    }

    # metadados commitados em results/[<scenario>/]<slug>/
    res_dir = scenario.results_dir(cfg.results_dir) / slug
    res_dir.mkdir(parents=True, exist_ok=True)
    (res_dir / "scores.json").write_text(
        json.dumps({"slug": slug, "agent": candidate.agent, "model": candidate.model,
                    "scenario": scenario.id,
                    "score": scored, "objective": objective, "judges": panel["per_judge"],
                    "divergences": panel["divergences"]},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (res_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    return result


def run_matrix(cfg: Config, only: list[str] | None = None, *,
               skip_agent: bool = False, scenario=None) -> list[dict]:
    scenario = scenario or get_scenario("cep_etl")
    candidates = [c for c in cfg.candidates if c.runs_scenario(scenario.id)]
    if only:
        candidates = [c for c in candidates if c.slug in only]
    results = []
    for c in candidates:
        results.append(run_candidate(cfg, c, scenario, skip_agent=skip_agent))
    return results


def rescore(cfg: Config, slug: str, scenario=None) -> dict:
    """Re-roda apenas as checagens objetivas no app já construído e recombina com as notas dos
    juízes já salvas (sem rebuildar nem re-invocar os juízes)."""
    scenario = scenario or get_scenario("cep_etl")
    candidate = cfg.candidate_by_slug(slug)
    if candidate is None:
        raise ValueError(f"slug desconhecido: {slug}")
    app_dir = scenario.run_dir(cfg.runs_dir, slug) / "app"
    if not app_dir.exists():
        raise FileNotFoundError(f"app não encontrado: {app_dir}")

    res_dir = scenario.results_dir(cfg.results_dir) / slug
    prior = json.loads((res_dir / "scores.json").read_text(encoding="utf-8"))
    judge_avg = {d: v.get("judge") for d, v in prior["score"]["dimensions"].items()}

    expected = _load_expected(cfg, scenario)
    objective = scenario.run_checks(app_dir, cfg.dataset_for(scenario.id), expected)
    git_res = gitcheck.check_git(app_dir, slug, cfg.git)
    objective["objective_by_dimension"]["git"] = git_res["note"]
    objective["git_detail"] = git_res

    scored = score_mod.compute_score(
        objective["objective_by_dimension"], judge_avg, objective["flags"], cfg, scenario,
    )

    prior["score"] = scored
    prior["objective"] = objective
    (res_dir / "scores.json").write_text(
        json.dumps(prior, ensure_ascii=False, indent=2), encoding="utf-8")
    result_file = res_dir / "result.json"
    if result_file.exists():
        result = json.loads(result_file.read_text(encoding="utf-8"))
        result["score"] = scored
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"objective": objective, "score": scored}


def selftest(cfg: Config, scenario=None) -> dict:
    """Valida o pipeline sem chamar agentes: usa o sample_app de teste como projeto gerado."""
    scenario = scenario or get_scenario("cep_etl")
    sample = scenario.sample_app
    if not sample.exists():
        raise FileNotFoundError(f"sample_app não encontrado em {sample}")

    slug = f"selftest-{scenario.id}"
    run_dir = scenario.run_dir(cfg.runs_dir, slug)
    app_dir = run_dir / "app"
    if app_dir.exists():
        shutil.rmtree(app_dir, ignore_errors=True)
        if app_dir.exists():
            # arquivos travados (ex.: .venv de execução anterior) — usa diretório novo
            import time as _t

            app_dir = run_dir / f"app-{int(_t.monotonic() * 1000)}"
    app_dir.mkdir(parents=True, exist_ok=True)
    for item in sample.iterdir():
        if item.name in {".venv", "__pycache__"}:
            continue
        dest = app_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, ignore=shutil.ignore_patterns("__pycache__", ".venv"))
        else:
            shutil.copy2(item, dest)

    # git: cria histórico de exemplo para exercitar gitcheck
    gitsetup.init_nested_repo(app_dir, slug, cfg.git)
    from benchmark.harness.adapters.base import run_command
    run_command(["git", "add", "-A"], cwd=app_dir, timeout=60)
    run_command(["git", "commit", "-q", "-m", "feat: aplicação inicial e interfaces"],
                cwd=app_dir, timeout=60)
    (app_dir / "README.md").write_text(
        (app_dir / "README.md").read_text(encoding="utf-8") + "\n", encoding="utf-8")
    run_command(["git", "add", "-A"], cwd=app_dir, timeout=60)
    run_command(["git", "commit", "-q", "-m", "docs: detalhes de uso no README"],
                cwd=app_dir, timeout=60)
    run_command(["git", "tag", "v0.1.0"], cwd=app_dir, timeout=60)

    expected = _load_expected(cfg, scenario)
    objective = scenario.run_checks(app_dir, cfg.dataset_for(scenario.id), expected)
    git_res = gitcheck.check_git(app_dir, slug, cfg.git)
    objective["objective_by_dimension"]["git"] = git_res["note"]

    # selftest não chama juízes (são pagos); pontua só com objetivo
    scored = score_mod.compute_score(
        objective["objective_by_dimension"], {d: None for d in objective["objective_by_dimension"]},
        objective["flags"], cfg, scenario,
    )
    return {"objective": objective, "git": git_res, "score": scored}
