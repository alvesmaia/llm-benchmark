# LLM Coding Benchmark — Gestão de Ativos de TI (3 fases)

Benchmark próprio para avaliar **LLMs operando como code agents**, inspirado na metodologia do
[Fábio Akita](https://akitaonrails.com/2026/04/24/llm-benchmarks-parte-3-deepseek-kimi-mimo/)
(repo de referência: [`akitaonrails/llm-coding-benchmark`](https://github.com/akitaonrails/llm-coding-benchmark)).

O foco é o que mais diferencia as ferramentas: **trabalho em etapas com mudança de direção**, que
estressa o **gerenciamento de contexto**. Cada candidato (**harness + modelo**) recebe o brief de um
cenário em **3 fases**, evolui o projeto sozinho via harness automatizado, e é pontuado por uma
**rubrica 0–100 em 12 dimensões** com **painel de 2 juízes** + um **juiz E2E** que usa a app como
usuário, classificando em tiers **A/B/C/D**.

## O desafio (`it_assets`)

Cenário único: **Gestão de Movimentação de Ativos de TI** (dispositivos × colaboradores: alocação,
devolução, transferência e manutenção), sobre uma base fictícia de movimentações. As **3 fases**
continuam a **mesma sessão** do agente (testa o gerenciamento de contexto na virada):

1. **Fase 1 — Dashboard:** planejar e implementar um **dashboard Streamlit** (Python 3.12 + uv) sobre a
   base. O modelo **copia** a base (de `DATASET_PATH`) para `data/` no projeto e passa a usá-la de lá.
2. **Fase 2 — Refatoração (pivô):** refatorar o dashboard numa **aplicação completa** — **FastAPI +
   SQLite + Jinja2**, com **JWT + RBAC**. Reaproveitar o código, reorganizar em camadas.
3. **Fase 3 — Perturbação dirigida (regressão):** o **harness muta valores** no CSV copiado em `data/`
   (campos nulos, ação fora do domínio, valor negativo, data em formato alternativo, id duplicado) e
   pede ao modelo para **rodar os testes e corrigir**. Mede robustez/depuração.

**Sem fase de git.** Pontua-se o **estado final** (pós-Fase 3). O resultado deve rodar com **um único
comando `uvx`**, já com o **`.env` versionado e preenchido** (carregado automaticamente). A estrutura
interna **não é imposta** — só o [contrato mínimo](benchmark/it_assets/brief/challenge.md) das
checagens. Mede-se **tempo** e **custo detalhado** (input/output/cache) **por fase**.

## Ranking: harness + modelo

O ranking é por **candidato = harness (agent) + modelo**, não só por modelo. O mesmo modelo conta como
entradas distintas conforme o harness (ex.: `claude_code-opus` vs `copilot_cli-copilot-opus`), porque o
harness influencia o resultado. Matriz em
[`benchmark/harness/config.yaml`](benchmark/harness/config.yaml).

## Dimensões (12, soma 100)

| # | Dimensão | Peso | Notas |
|---|----------|-----:|-------|
| 1 | **Refatoração** ★ | 13 | qualidade da virada Streamlit→FastAPI/SQLite/JWT/RBAC (camadas/reaproveitamento) |
| 2 | **Resiliência** ★ | 12 | recupera-se da perturbação da base (testes + boot voltam a passar) |
| 3 | **E2E** ★ | 11 | um agente Playwright/Sonnet usa a UI: login, dashboard, ação restrita bloqueada |
| 4 | **Auth JWT** ★ | 10 | login 200/401; rotas protegidas exigem Bearer |
| 5 | **RBAC** ★ | 10 | ≥2 papéis; ação restrita negada com 403 |
| 6 | **Dashboard** | 9 | métricas de movimentação coerentes |
| 7 | **Persistência** | 8 | SQLite, schema/índices, carga da base |
| 8 | **Testes** | 8 | cobertura medida (**alvo oculto**); testes passam |
| 9 | **API/Web** | 7 | endpoints REST + telas Jinja2 |
| 10 | **Execução `uvx`** ★ | 6 | um único comando sobe a app lendo o `.env` versionado |
| 11 | **Ingestão** | 4 | leitura/parse da base de movimentações |
| 12 | **Produção** | 2 | README, lint (ruff), empacotamento uv/uvx |

★ = diferenciadores (etapas + gerenciamento de contexto). Rubrica humana:
[`rubric.md`](benchmark/it_assets/rubric/rubric.md).

## Ranking

> Seção **gerada** ao final de `uv run bench run` (ou `uv run bench report`).
> Ver também [`results/leaderboard.md`](results/leaderboard.md).

<!-- LEADERBOARD:START -->

Ranking por **candidato = harness (agent) + modelo**. O mesmo modelo aparece como
entradas distintas conforme o harness (o harness influencia o resultado).

Ordenado por **Subtotal** (soma ponderada 0–100 pré-modificadores), que diferencia melhor
que o Score final — este satura no teto 100 e inclui bônus/penalidades.

### Legenda das colunas

- **#** — posição no ranking (ordenado pelo Subtotal)
- **Harness** — o code agent que dirigiu o modelo (ex.: `claude_code`, `copilot_cli`)
- **Modelo** — modelo avaliado; tag `· 1M` quando rodou em contexto de 1M
- **Thinking** — esforço de raciocínio declarado (default predefinido `medium`; candidatos podem sobrescrever, ex.: `xhigh`/`high`)
- **Subtotal** — soma ponderada das dimensões (0–100, **antes** dos modificadores) — critério de ordenação
- **Score** — Subtotal + modificadores (bônus de performance, penalidades), com teto 100
- **Tier** — faixa do Score: A (80+), B (60–79), C (40–59), D (<40)
- **Tempo** — tempo total de conclusão (soma das 3 fases: dashboard + refactor + correção)

Dimensões avaliadas (nota 0–100 por dimensão · peso na rubrica):

- **Refatoração** (peso 13) — qualidade da virada Streamlit→FastAPI/SQLite/Jinja2/JWT/RBAC: reaproveitamento do código do dashboard e organização em camadas coesas
- **Resiliência** (peso 12) — recuperação após a perturbação dirigida da base (Fase 3): testes e boot voltam a passar sobre os dados mutados; ingestão/validação robustas
- **E2E** (peso 11) — veredito de um agente Playwright/Sonnet que usa a app como usuário: login, dashboard e bloqueio de ação restrita (% de passos OK)
- **Auth JWT** (peso 10) — JWT: login válido→token / inválido→401; rotas protegidas exigem Bearer (401 sem)
- **RBAC** (peso 10) — RBAC: ≥2 papéis; ação de escrita/admin negada com 403 ao papel sem permissão
- **Dashboard** (peso 9) — métricas úteis de movimentação (por status/local/colaborador/tempo) coerentes
- **Persistência** (peso 8) — SQLite: schema/índices e carga a partir da base
- **Testes** (peso 8) — testes pytest com cobertura medida (alvo OCULTO); devem passar
- **API/Web** (peso 7) — endpoints REST + telas Jinja2 que respondem HTML
- **Execução uvx** (peso 6) — um único comando `uvx` sobe a app lendo o `.env` versionado
- **Ingestão** (peso 4) — leitura/parse da base de movimentações de ativos de TI
- **Produção** (peso 2) — README com o comando único, lint (ruff), empacotamento uv/uvx

- **Tokens In** — tokens de entrada somados nas 3 fases (— quando o CLI não reporta)
- **Tokens Out** — tokens de saída somados nas 3 fases (— quando o CLI não reporta)
- **Cache** — tokens de cache (escrita + leitura) somados nas 3 fases
- **Interações** — nº de turns/passos do agente somados nas 3 fases (— quando o CLI não reporta)
- **Custo (US$)** — custo-equivalente estimado das fases (referência; o consumo conta no plano)
- **Cobertura (%)** — cobertura de testes medida pelo harness (dimensão `tests`, alvo oculto)
- **Divergências** — dimensões com divergência grande entre os juízes (sinalizadas p/ revisão)

| # | Harness | Modelo | Thinking | Subtotal | Score | Tier | Tempo | Refatoração | Resiliência | E2E | Auth JWT | RBAC | Dashboard | Persistência | Testes | API/Web | Execução uvx | Ingestão | Produção | Tokens In | Tokens Out | Cache | Interações | Custo (US$) | Cobertura (%) | Divergências |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude_code | Opus 4.8 · 1M | medium | **94.2** | 97.2 | A | 28m 24s | 92 | 100 | 100 | 100 | 100 | 82 | 98 | 99 | 59 | 100 | 100 | 100 | 10 751 | 82 892 | 8 835 049 | 105 | 8.946 | 98 | — |
| 2 | claude_code | Opus 4.7 · 1M | medium | **93.0** | 96.0 | A | 17m 9s | 88 | 100 | 100 | 100 | 100 | 75 | 98 | 99 | 59 | 100 | 100 | 100 | 100 | 58 741 | 7 166 880 | 88 | 7.065 | 94 | — |
| 3 | copilot_cli | Opus 4.7 · 1M | medium | **92.8** | 95.8 | A | 17m 43s | 89 | 97 | 100 | 99 | 99 | 81 | 96 | 98 | 58 | 99 | 99 | 99 | — | — | — | — | — | 89 | — |
| 4 | claude_code | Sonnet 4.6 | medium | **91.3** | 94.3 | A | 21m 6s | 86 | 97 | 100 | 98 | 98 | 80 | 90 | 96 | 58 | 98 | 97 | 96 | 83 | 65 261 | 6 292 597 | 85 | 4.356 | 90 | — |
| 5 | claude_code | Haiku 4.5 | high | **37.2** | 40.2 | C | 19m 32s | 40 | 44 | 25 | 6 | 4 | 42 | 91 | 2 | 9 | 96 | 98 | 71 | 916 | 70 294 | 12 270 093 | 166 | 2.146 | — | — |

## Modificadores aplicados

- **claude_code-claude-opus-4-8**: load_performance_bonus (+3)
- **claude_code-claude-opus-4-7**: load_performance_bonus (+3)
- **copilot_cli-claude-opus-4.7**: load_performance_bonus (+3)
- **claude_code-sonnet**: load_performance_bonus (+3)
- **claude_code-claude-haiku-4-5-20251001**: load_performance_bonus (+3)
<!-- LEADERBOARD:END -->

## Como o custo (US$) e os tokens são calculados

As colunas **Tokens In/Out/Cache** e **Custo (US$)** vêm do que o CLI do agente reporta, **somado pelas
3 fases**. O Claude Code reporta `usage` (input/output/cache) e `total_cost_usd`; o opencode soma o
`tokens`/`cost` dos eventos `step_finish`. Copilot e Codex **não** dão dados estruturados → aparecem `—`.

```
custo_fase = (input_tokens        × preço_input)
           + (output_tokens       × preço_output)
           + (cache_write_tokens  × preço_cache_write)
           + (cache_read_tokens   × preço_cache_read)      # preços por token = US$/1M ÷ 1.000.000

custo_total = Σ custo_fase  (dashboard + refactor + correção)
```

> ⚠️ **Não é cobrança real.** O benchmark roda na **assinatura Claude Max (5x)** — o consumo conta
> contra os limites do plano, **não** é faturado por token. Esse valor é só uma **estimativa de
> referência** (o que custaria via API) para comparar a eficiência dos candidatos.

### Preços por token (US$ por 1M tokens)

| Modelo | Input | Output | Cache write | Cache read |
|--------|------:|-------:|------------:|-----------:|
| Opus 4.8 (`claude-opus-4-8`) | 5,00 | 25,00 | 10,00 | 0,50 |
| Opus 4.7 (`claude-opus-4-7`) | 5,00 | 25,00 | 10,00 | 0,50 |
| Sonnet 4.6 (`claude-sonnet-4-6`) | 3,00 | 15,00 | 6,00 | 0,30 |
| GPT-5.4 (Codex, conta ChatGPT) | — | — | — | — |

- **Cache write/read** seguem os multiplicadores do prompt caching da Anthropic sobre o preço de input:
  **write = 2× (TTL 1 h)**; **read = 0,1×**. O Claude Code usa cache de **1 h**.
- O **Codex (GPT-5.4)** e o **Copilot** rodam via outras contas e **não reportam** o custo/tokens —
  por isso aparecem como `—` no ranking.

## Como funciona

1. **Fase 1 (dashboard):** o agente recebe o brief e constrói o dashboard Streamlit, headless, num
   diretório isolado, copiando a base para `data/`.
2. **Fase 2 (refactor):** continua a mesma sessão e refatora para FastAPI + SQLite + Jinja2 + JWT + RBAC.
3. **Fase 3 (correção):** o harness **muta a base** em `data/` e o agente roda os testes e corrige.
4. **Checagens objetivas:** o harness roda `pytest --cov` (captura a cobertura), `ruff`, sobe a app via
   **`uvx`** lendo o `.env`, e verifica JWT (200/401), RBAC (403), Web (form de login), SQLite populado e
   a recuperação pós-perturbação (`resiliencia`).
5. **Juiz E2E (Playwright/Sonnet):** um agente Sonnet dirige o browser como usuário — login, dashboard e
   tentativa de ação restrita — e devolve um veredito JSON que alimenta a dimensão `e2e`. Indisponível em
   headless/cron → a dimensão cai para fallback sem quebrar o pipeline.
6. **Painel de 2 juízes:** dois modelos pontuam a rubrica de forma independente; a nota de cada dimensão é
   a **média** (reduz viés; divergências grandes são sinalizadas).
7. **Score + leaderboard:** combina objetivo + juízes ponderado pela rubrica, aplica modificadores e tier.
   Opcionalmente, **exporta um ZIP por candidato** (app + prompt do juiz) para reavaliação por juiz externo.

## Uso

```bash
# instalar deps do harness (uv gerencia o Python)
uv sync

# gerar a fixture sintética (CSV + expected.json) — gitignored
uv run python benchmark/it_assets/fixtures/_generate.py

# self-test do harness contra a fixture + sample_app (não chama agentes/juízes pagos nem o E2E)
uv run bench selftest

# rodar a matriz completa (dirige claude/copilot via assinatura mensal, modo headless)
uv run bench run

# rodar um candidato específico
uv run bench run --only claude_code-opus-4-8

# pontuar e gerar o leaderboard
uv run bench report

# exportar, por candidato, um ZIP (app + prompt do juiz) p/ reavaliação por juiz externo
uv run bench export <slug>

# subir a app gerada por um candidato em um único comando (FastAPI/Web)
uv run bench serve claude_code-sonnet
# ...ou standalone, direto no projeto gerado (lê o .env versionado; sobe COM a base):
cd <runs_dir>/claude_code-sonnet/app && uvx --from . it-assets serve --host 127.0.0.1 --port 8000
```

## Dataset

O dataset de movimentação de ativos de TI é uma **fixture sintética determinística** (gitignored; só o
gerador `_generate.py` e um `expected.json` mínimo são versionados). O caminho é servido aos agentes via
`DATASET_PATH`; a Fase 1 copia a base para `data/` no projeto (app autossuficiente). A **mesma base** é
usada por todos. O `.env` versionado COM valores é intencional (validação por 1 comando) — apenas valores
de demonstração, nunca segredos reais.

## Isolamento

Cada projeto gerado fica num diretório **fora do repo** (`runs_dir` absoluto externo, em `config.yaml`),
para que o agente não enxergue a rubrica, o brief nem o `sample_app`. Há um `.git` aninhado só para
isolamento — **sem fase de git** neste cenário (não há commits/tag/push).

## Estrutura

Ver [`CLAUDE.md`](CLAUDE.md) e [`docs/methodology.md`](docs/methodology.md) para a justificativa dos pesos
e a adaptação da metodologia do Akita.
