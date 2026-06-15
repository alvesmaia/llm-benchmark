# CLAUDE.md — Guia para contribuir no llm-benchmark

Instruções para um agente de código (Claude Code ou similar) trabalhar neste repositório.
Leia antes de editar. As regras em **"Regras críticas"** foram aprendidas em execuções reais — não as regrida.

## O que é

Benchmark de **LLMs operando como code agents**, inspirado na metodologia do Fábio Akita. Cenário único
**`it_assets`** (Gestão de Movimentação de Ativos de TI): os candidatos recebem o brief em **3 fases que
continuam a mesma sessão** — (1) **dashboard Streamlit**, (2) **pivô** para FastAPI + SQLite + Jinja2 +
JWT + RBAC, (3) o **harness muta a base** copiada e o modelo **corrige** (perturbação dirigida). Foco em
**trabalho em etapas + gerenciamento de contexto**. **Sem fase de git;** pontua-se o **estado final**.
Rubrica de **12 dimensões (0–100)** com **painel de 2 juízes** + **juiz E2E** (Playwright/Sonnet). O app
roda por **um único `uvx`** com `.env` versionado. Contexto: [`docs/methodology.md`](docs/methodology.md).

## Setup

Requer **uv** (gerencia o Python). Não use `pip`/`python` direto.

```bash
uv sync
uv run bench selftest   # valida o pipeline ponta a ponta SEM chamar agentes pagos
```

## Antes de commitar (obrigatório — verifique, não presuma)

```bash
uv run ruff check benchmark    # deve imprimir "All checks passed!"
uv run pytest -q               # testes do harness devem passar
uv run bench selftest          # deve terminar em Tier A ("Self-test OK.")
```

Commits em **Conventional Commits** (`feat:`, `fix:`, `docs:`, `style:`, `test:`, `chore:`). Encerre a
mensagem com a linha de co-autoria do agente, quando aplicável.

## Estrutura

```
benchmark/
  it_assets/    conteúdo do cenário único:
                  brief/        challenge.md (contrato mínimo) + phase1/2/3_prompt.md
                  rubric/       rubric.md + judge_prompt.md (12 dimensões)
                  fixtures/     _generate.py (gera CSV + expected.json; CSV gitignored) + perturb_dataset
                  checks.py     checagens objetivas do cenário
                  sample_app/   app de referência (FastAPI+SQLite+Jinja2+JWT+RBAC) — fecha o selftest Tier A
  harness/      código do harness:
                  config.py (carrega config.yaml)    rubric.py (tiers + reexport das dims de it_assets)
                  checks.py (helpers genéricos)      gitcheck.py / gitsetup.py (git, isolamento)
                  judge.py (painel de juízes)        e2e_judge.py (juiz E2E Playwright/Sonnet)
                  score.py (obj+juiz → score+tier)   report.py (leaderboard + colunas)
                  run_benchmark.py (orquestrador)    cli.py (comando `bench`)
                  scenarios/ (base.py + registry.py + it_assets.py)   adapters/ (um por agente)
  tests/harness/  testes unitários do harness (pytest)
results/        metadados/scores commitados + leaderboard.md (GERADO)
docs/           methodology.md
config: benchmark/harness/config.yaml
```

## Conceitos-chave

- **Candidato = harness (agent) + modelo.** `slug = <agent>-<model_slug>`. O mesmo modelo conta como
  entradas distintas conforme o harness.
- **3 fases (continuam a MESMA sessão):** (1) dashboard Streamlit, (2) pivô FastAPI/SQLite/JWT/RBAC,
  (3) o harness muta a base (`pre_phase_hooks={2: perturb_dataset}`) e o modelo corrige. **Sem git.**
  `run_benchmark.run_candidate` itera `scenario.phase_prompts` (build no índice 0, `continue_session`
  nos demais), roda o hook ANTES da fase indicada, e só toca git se `scenario.has_git_phase`.
- **Rubrica:** 12 dimensões somando 100 — **fonte canônica em `harness/scenarios/it_assets.py`**
  (`rubric.py` reexporta + tiers; `rubric.md` é a versão humana). Diferenciadores (★): refactor,
  resiliencia, e2e, auth_jwt, rbac, execucao_uvx.
- **Painel de 2 juízes** (config: `judges`): cada um pontua de forma independente; tira-se a média.
  O juiz do **mesmo agente E mesma família de modelo** do candidato é pulado (anti-viés) — ver `judge.py`.
- **Juiz E2E** (`harness/e2e_judge.py`, config `e2e_judge`): sobe a app via `uvx` e um agente Sonnet
  dirige o browser via Playwright MCP (login/dashboard/ação restrita) → nota objetiva da dimensão `e2e`.
  Robusto: MCP/app indisponível ⇒ `e2e=None` e o pipeline segue. O selftest NÃO chama o E2E.
- **Custo detalhado por fase.** `PhaseResult` carrega `tokens_input/output/cache_write/cache_read`
  (claude_code lê `usage`; opencode soma `step_finish`; copilot/codex ficam `—`). `report.py` soma por
  candidato e adiciona colunas **Tokens In · Tokens Out · Cache · Custo · Cobertura (%)**.
- **Ranking por Subtotal** (soma ponderada pré-modificadores) — diferencia melhor que o Score final.
- **Thinking default = `medium`.** O campo `thinking` tem default `medium`; candidatos podem sobrescrever
  (ex.: `xhigh`). `effort` (flag `--effort` do Claude Code) é separado e opt-in.

## Comandos do harness (`bench`)

```bash
uv run bench run [--only slug1,slug2] [--skip-agent] [--no-export]
uv run bench rescore <slug>      # re-roda checagens objetivas + reaproveita juízes
uv run bench score | report      # regenera o leaderboard e injeta no README
uv run bench export <slug>       # ZIP do app + prompt do juiz + resultados (juiz externo)
uv run bench serve <slug>        # sobe a app do projeto gerado (um comando uvx/uv run)
uv run bench selftest            # valida o pipeline contra a fixture + sample_app (sem agentes pagos)
```

Há um único cenário (`it_assets`, default); `--scenario` ainda existe mas só aceita `it_assets`.
`--skip-agent` re-avalia um app já construído (re-roda checagens + juízes, sem rebuildar). `bench run`
gera, por candidato, um **ZIP** em `exports/it_assets/<slug>.zip` (app + `judge_prompt.md` + scores/
result) para reavaliação por um juiz externo — desligue com `--no-export`.

## Regras críticas (não regredir)

1. **Isolamento — `runs_dir` DEVE ficar FORA do repo.** Em `config.yaml`, `runs_dir` é um caminho
   absoluto externo (ex.: `C:/PROJETOS/llm-benchmark-runs`). Se o diretório do candidato ficar dentro do
   repo, o agente enxerga (e copia/contamina-se com) a rubrica, o brief e o `sample_app`. Já aconteceu.
2. **Prompts aos CLIs via STDIN, não argv.** Prompts grandes (especialmente o do juiz) estouram o limite
   de linha de comando no Windows (WinError 206). Os adapters e o `judge.py` passam o prompt por stdin
   (`run_command(..., stdin_text=prompt)`). Exceção: o Copilot não lê stdin → o juiz Copilot lê o prompt
   de um arquivo via tools.
3. **Isolamento git (sem fase de git neste cenário).** `gitsetup.py` cria o repo aninhado já na branch
   `run/<slug>` só para isolamento; como `has_git_phase=False`, NÃO há commits/tag/push nem dimensão git.
   Nunca volte a usar branch `main` no app gerado.
4. **Checagens são caixa-preta e tolerantes.** `it_assets/checks.py` descobre o console script no
   `pyproject.toml`, sobe via `uvx`, e testa contrato (login/RBAC/web/persistência) por HTTP. A estrutura
   interna do projeto é livre — não engesse caminhos/nomes. Falha vira nota 0 com detalhe, nunca exceção.
5. **Score renormaliza dimensões sem fonte.** Uma dimensão sem objetivo nem juiz é **excluída** e os pesos
   renormalizam (não zera, ex.: `refactor` sem juiz). Ver `score.py`.
6. **O leaderboard no README é GERADO.** Fica entre `<!-- LEADERBOARD:START -->` e `<!-- ...END -->`; é
   reescrito por `bench run`/`report`/`rescore` a partir de `results/*/scores.json`. **Não edite à mão** —
   rode `bench report`. Conteúdo fora dos marcadores (ex.: a seção de custo) é estático e seguro de editar.
7. **Lint:** ruff com `line-length = 100`. Typer dispara B008 (ignorado só em `cli.py`); o `_generate.py`
   da fixture tem E501 ignorado (tabelas largas); o `sample_app` é `extend-exclude` (tem ruff próprio).
8. **Nunca instrua o agente a rodar um servidor bloqueante.** `it-assets serve`/Streamlit não retornam; um
   agente cujo shell bloqueia neles trava a sessão por horas. Os prompts de fase pedem boot em
   **background/timeout + encerrar** — a avaliação (`checks._server_checks`/`e2e_judge`) sobe e mata o
   servidor por conta própria. Não reintroduza "rode `serve` e confirme" sem essa ressalva.
9. **`bench selftest` DEVE fechar Tier A.** O `it_assets/sample_app` é o gabarito do pipeline objetivo
   (não do desafio): toda mudança em checks/scenario tem de manter `selftest` em Tier A. Ao adicionar um
   cenário no futuro, crie `harness/scenarios/<id>.py` (instância `SCENARIO`), registre em
   `scenarios/registry.py`, ponha brief/rubric/checks/fixture/sample_app sob `benchmark/<id>/`, e garanta
   `bench selftest --scenario <id>` em **Tier A**.

## Como adicionar um candidato

Edite `benchmark/harness/config.yaml` em `candidates:`:

```yaml
- agent: claude_code        # deve existir um adapter (ver abaixo)
  model: claude-opus-4-8    # string que o CLI do agente aceita
  model_slug: opus-4-8      # compõe o slug: claude_code-opus-4-8
  display: "Opus 4.8"       # nome limpo no ranking
  context: "1M"             # opcional; "1M" mostra a tag "· 1M" no ranking
```

## Como adicionar um novo agente (adapter)

1. Crie `benchmark/harness/adapters/<nome>.py` com uma classe que herda `Adapter` e implementa
   `build()` e `continue_session()`. **Passe o prompt por stdin** (Regra 2). Capture `session_id` para
   continuar a sessão nas fases 2/3 quando o CLI suportar.
2. Registre em `adapters/base.py` → `get_adapter()`.
3. Adapters existentes como referência: `claude_code` (`claude -p`), `copilot_cli` (`copilot -p`),
   `codex_cli` (`codex exec`).

## Plataforma / assinaturas

- Roda via **CLIs logados** (Claude Max, GitHub Copilot, ChatGPT/Codex) — **sem API key**. Não configure
  `ANTHROPIC_API_KEY` etc.; os adapters herdam o login.
- As colunas **Tokens/Custo (US$)** são **custo-equivalente em API** (referência), não faturamento — ver
  "Como o custo e os tokens são calculados" no README. Copilot/Codex não reportam → `—`.
- **1M de contexto:** Opus 4.7/4.8 funcionam; `sonnet[1m]` exige *usage credits* (pode falhar).
- **Juiz E2E (Playwright/Sonnet):** indisponível em headless/cron ⇒ `e2e=None`, pipeline segue.
- **Copilot GPT/Gemini** podem ficar indisponíveis (cota de *premium requests* esgotada).

## Dataset (it_assets)

Fixture sintética determinística de movimentação de ativos de TI, gerada por
`benchmark/it_assets/fixtures/_generate.py` (**CSV gitignored**; só `_generate.py` + `expected.json`
versionados). Servida via `DATASET_PATH`; a Fase 1 copia para `data/` no projeto. O CSV em
`sample_app/data/` É versionado (o sample_app precisa ser autossuficiente). O `.env` versionado COM
valores é intencional (validação por 1 comando) — só valores de demo, nunca segredos reais.

## Windows

- Shell é PowerShell; exporte `PYTHONIOENCODING=utf-8` ao rodar o harness.
- Um `.venv` de run anterior pode ficar travado; o `selftest` usa um subdiretório novo se o `rmtree` falhar.
