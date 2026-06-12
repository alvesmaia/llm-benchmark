# CLAUDE.md — Guia para contribuir no llm-benchmark

Instruções para um agente de código (Claude Code ou similar) trabalhar neste repositório.
Leia antes de editar. As regras em **"Regras críticas"** foram aprendidas em execuções reais — não as regrida.

## O que é

Benchmark de **LLMs operando como code agents**, inspirado na metodologia do Fábio Akita. Todos os
candidatos recebem o **mesmo brief** (um ETL da base de CEP dos Correios em Python, com CLI + API + Web),
constroem o projeto sozinhos via harness headless em **3 fases** (build → validação → git), e são pontuados
por uma **rubrica de 9 dimensões (0–100)** com **painel de 2 juízes**. Contexto completo:
[`docs/methodology.md`](docs/methodology.md).

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
  brief/        challenge.md (o desafio) + phase1/2/3_prompt.md
  rubric/       rubric.md, judge_prompt.md, objective_checks.md (docs da metodologia)
  harness/      código do harness:
                  config.py (carrega config.yaml)    rubric.py (pesos/tiers — FONTE CANÔNICA)
                  checks.py (checagens objetivas)    gitcheck.py / gitsetup.py (git)
                  judge.py (painel de juízes)        score.py (combina obj+juiz → score+tier)
                  report.py (leaderboard)            run_benchmark.py (orquestrador)
                  cli.py (comando `bench`)           adapters/ (um por agente)
  fixtures/     dne_sample/ (fixture DNE sintética, Latin-1) + expected_queries.json
  tests/
    harness/    testes unitários do harness (pytest)
    sample_app/ app de referência usado SÓ pelo selftest (não é gabarito do desafio)
results/        metadados/scores commitados + leaderboard.md (GERADO)
runs/           gitignored (mas os projetos gerados ficam FORA do repo — ver Regra 1)
docs/           methodology.md
config: benchmark/harness/config.yaml
```

## Conceitos-chave

- **Candidato = harness (agent) + modelo.** `slug = <agent>-<model_slug>`. O mesmo modelo conta como
  entradas distintas conforme o harness.
- **3 fases:** build, validação (boot/testes/lint), git (commits + tag semver + push).
- **Rubrica:** 9 dimensões com pesos que somam 100 — definidos em `harness/rubric.py` (a fonte da verdade;
  `rubric.md` é a versão humana). Combinação objetivo×juiz em `objective_checks.md`.
- **Painel de 2 juízes** (config: `judges`): cada um pontua de forma independente; tira-se a média.
  O juiz do **mesmo agente E mesma família de modelo** do candidato é pulado (anti-viés) — ver
  `judge.py`. Atenção: harness diferente NÃO é pulado (ex.: o candidato Sonnet-via-Copilot é julgado
  pelo juiz Sonnet-via-Claude-Code, pois o agente difere).
- **Ranking por Subtotal** (soma ponderada pré-modificadores) — diferencia melhor que o Score final,
  que satura no teto 100.
- **Cenários (multi-desafio).** O harness é parametrizado por `Scenario` (`harness/scenarios/`): cada
  cenário define dimensões/pesos/combinação, brief, rubrica, checks, dataset, sample_app e layout próprios.
  `cep_etl` é o default (ETL CEP); `inventory` é o 2º desafio (Gestão de Estoque, car-sales). Cada candidato
  declara em `config.yaml` quais cenários roda (campo `scenarios:`; ausente ⇒ só `cep_etl`). Resultados e
  leaderboard são namespaced por cenário (cep usa a raiz; novos usam subpasta, ex.: `results/inventory/`).
- **Thinking default = `medium`.** O campo `thinking` (rótulo do ranking) tem default `medium`; candidatos
  podem sobrescrever (ex.: `xhigh`). `effort` (flag `--effort` do Claude Code) é separado e opt-in.

## Comandos do harness (`bench`)

```bash
uv run bench run [--only slug1,slug2] [--skip-agent] [--scenario cep_etl|inventory] [--no-export]
uv run bench rescore <slug> [--scenario ...]   # re-roda checagens objetivas + reaproveita juízes
uv run bench score | report [--scenario ...]    # regenera o leaderboard do cenário e injeta no README
uv run bench export <slug> [--scenario ...]     # ZIP do app + prompt do juiz + resultados (juiz externo)
uv run bench serve <slug>        # sobe Web+API do projeto gerado (um comando)
uv run bench query <slug> <ceps...>
uv run bench selftest [--scenario cep_etl|inventory]
```

`--skip-agent` re-avalia um app já construído (re-roda checagens + juízes, sem rebuildar). `--scenario`
default é `cep_etl` (comportamento histórico). `bench run` gera, por candidato, um **ZIP** em
`exports/<cenário>/<slug>.zip` (app + `judge_prompt.md` + scores/result) para reavaliação por um juiz
externo — desligue com `--no-export`. O `judge_prompt.md` é o **mesmo** prompt do painel interno.

## Regras críticas (não regredir)

1. **Isolamento — `runs_dir` DEVE ficar FORA do repo.** Em `config.yaml`, `runs_dir` é um caminho
   absoluto externo (ex.: `C:/PROJETOS/llm-benchmark-runs`). Se o diretório do candidato ficar dentro do
   repo, o agente enxerga (e copia/contamina-se com) a rubrica, o brief e o `sample_app`. Já aconteceu.
2. **Prompts aos CLIs via STDIN, não argv.** Prompts grandes (especialmente o do juiz) estouram o limite
   de linha de comando no Windows (WinError 206). Os adapters e o `judge.py` passam o prompt por stdin
   (`run_command(..., stdin_text=prompt)`). Exceção: o Copilot não lê stdin → o juiz Copilot lê o prompt
   de um arquivo via tools.
3. **Git do agente não pode tocar o `main`.** `gitsetup.py` cria o repo aninhado já na branch `run/<slug>`
   e só configura `origin` quando `push_enabled: true`. Nunca volte a usar branch `main` no app gerado.
4. **Matcher de endereço é tolerante.** `checks._address_matches` é **recursivo** (acha campos em qualquer
   nível, ex.: `{"endereco": {...}}`) e aceita sinônimos. Não volte a assumir JSON plano — isso reprovava
   ETLs corretos.
5. **Score renormaliza dimensões sem fonte.** Uma dimensão sem objetivo nem juiz é **excluída** e os pesos
   renormalizam (não zera, ex.: Arquitetura sem juiz). Ver `score.py`.
6. **O leaderboard no README é GERADO.** Fica entre `<!-- LEADERBOARD:START -->` e `<!-- ...END -->`; é
   reescrito por `bench run`/`report`/`rescore` a partir de `results/*/scores.json`. **Não edite à mão** —
   rode `bench report`. Conteúdo fora dos marcadores (ex.: a seção de custo) é estático e seguro de editar.
7. **Lint:** ruff com `line-length = 100`. Typer dispara B008 (ignorado só em `cli.py` via per-file-ignore).
8. **Nunca instrua o agente a rodar um servidor bloqueante.** `cep-etl serve` não retorna; um agente cujo
   shell bloqueia nele (ex.: Codex/GPT-5.4) trava a sessão inteira por horas. Os prompts de fase pedem boot
   em **background/timeout + encerrar** — a avaliação automatizada (`checks._server_checks`) já sobe e mata
   o servidor por conta própria. Não reintroduza "rode `serve` e confirme" sem essa ressalva.
9. **Cenários são ADITIVOS — nunca quebre o `cep_etl`.** Toda parametrização por `Scenario` tem default
   `cep_etl` (resultados/leaderboard/brief do CEP intocados). Ao adicionar um cenário, crie
   `harness/scenarios/<id>.py` (instância `SCENARIO`), registre em `scenarios/registry.py`, e ponha brief/
   rubric/checks/fixture/sample_app sob `benchmark/<id>/`. O sample_app DEVE fechar
   `bench selftest --scenario <id>` em **Tier A** e o `bench selftest` (cep) NÃO pode regredir.

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
- A coluna **Custo (US$)** é **custo-equivalente em API** (referência), não faturamento — ver a seção
  "Como o custo é calculado" no README.
- **1M de contexto:** Opus 4.7/4.8 funcionam; `sonnet[1m]` exige *usage credits* (pode falhar).
- **Copilot GPT/Gemini** podem ficar indisponíveis (cota de *premium requests* esgotada) — o painel cai
  para juízes Claude (Opus + Sonnet).

## Base DNE

A base oficial dos Correios é **proprietária — nunca versione** (já está no `.gitignore`). Por padrão
`config.yaml` aponta `dne_path` para a fixture sintética. Para avaliação real, aponte para uma pasta com
os arquivos `LOG_*.TXT` (encoding Latin-1, separador `@`).

## Windows

- Shell é PowerShell; exporte `PYTHONIOENCODING=utf-8` ao rodar o harness.
- Um `.venv` de run anterior pode ficar travado; o `selftest` usa um subdiretório novo se o `rmtree` falhar.
