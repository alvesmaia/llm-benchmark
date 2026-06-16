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
    p1 = _phase_prompt(scenario, scenario.phase_prompts[0])
    challenge_file = scenario.brief_dir / "challenge.md"
    if challenge_file.exists():
        return f"{p1}\n\n{challenge_file.read_text(encoding='utf-8')}"
    return p1


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
    scenario = scenario or get_scenario()
    slug = candidate.slug
    run_dir = scenario.run_dir(cfg.runs_dir, slug)
    app_dir = run_dir / "app"
    logs_dir = run_dir / "logs"
    # Re-run limpo: um build fresco NÃO pode reaproveitar o app/logs de um run anterior (senão o
    # agente constrói por cima do resultado antigo — contaminação — e logs/cost ficam obsoletos).
    # Em --skip-agent preservamos (re-avalia o app existente).
    if not skip_agent and run_dir.exists():
        shutil.rmtree(app_dir, ignore_errors=True)
        for old in logs_dir.glob("*.json") if logs_dir.exists() else []:
            old.unlink(missing_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    app_dir.mkdir(parents=True, exist_ok=True)

    started = datetime.now(UTC).isoformat()
    phases = {}

    if not skip_agent:
        # repo aninhado p/ isolamento; só faz commits/push se o cenário tiver fase de git.
        git_info = gitsetup.init_nested_repo(app_dir, slug, cfg.git)
        (logs_dir / "gitsetup.json").write_text(json.dumps(git_info, indent=2), encoding="utf-8")

        adapter = get_adapter(candidate.agent, candidate.model, effort=candidate.effort)
        env = _agent_env(cfg, app_dir, scenario)

        prev = None
        for idx, name in enumerate(scenario.phase_prompts):
            # hook ANTES desta fase (ex.: perturbar a base copiada antes da Fase 3)
            hook = scenario.pre_phase_hooks.get(idx)
            if hook is not None:
                try:
                    hook(app_dir)
                except Exception as e:  # noqa: BLE001 - hook nunca derruba o pipeline
                    (logs_dir / f"hook_phase{idx + 1}.json").write_text(
                        json.dumps({"error": str(e)}, indent=2), encoding="utf-8")

            phase = f"phase{idx + 1}"
            prompt = (_build_phase1_prompt(scenario) if idx == 0
                      else _phase_prompt(scenario, name))
            if idx == 0:
                res = adapter.build(prompt, app_dir, env)
            else:
                res = adapter.continue_session(phase, prompt, app_dir, env, prev)
            phases[phase] = res.to_dict()
            (logs_dir / f"{phase}.json").write_text(
                json.dumps(res.to_dict(), indent=2), encoding="utf-8")
            prev = res

        if scenario.has_git_phase:
            push_res = gitsetup.push_results(app_dir, slug, cfg.git)
            (logs_dir / "push.json").write_text(json.dumps(push_res, indent=2), encoding="utf-8")

    # ----- avaliação -----
    expected = _load_expected(cfg, scenario)
    objective = scenario.run_checks(app_dir, cfg.dataset_for(scenario.id), expected)

    if scenario.has_git_phase:
        git_res = gitcheck.check_git(app_dir, slug, cfg.git)
        objective["objective_by_dimension"]["git"] = git_res["note"]
        objective["git_detail"] = git_res

    # juiz E2E (Playwright/Sonnet): nota objetiva da dimensão e2e (quando o cenário a tem)
    if "e2e" in scenario.dimensions:
        from benchmark.harness import e2e_judge
        e2e_res = e2e_judge.run_e2e(app_dir, logs_dir, scenario, cfg)
        if e2e_res.get("note") is not None:
            objective["objective_by_dimension"]["e2e"] = e2e_res["note"]
        objective["e2e_detail"] = e2e_res

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
    scenario = scenario or get_scenario()
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
    scenario = scenario or get_scenario()
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
    if scenario.has_git_phase:
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
    scenario = scenario or get_scenario()
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

    git_res = None
    if scenario.has_git_phase:
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
    if scenario.has_git_phase:
        git_res = gitcheck.check_git(app_dir, slug, cfg.git)
        objective["objective_by_dimension"]["git"] = git_res["note"]

    # selftest não chama juízes (são pagos) nem o juiz E2E; pontua só com objetivo
    scored = score_mod.compute_score(
        objective["objective_by_dimension"], {d: None for d in objective["objective_by_dimension"]},
        objective["flags"], cfg, scenario,
    )
    return {"objective": objective, "git": git_res, "score": scored}
