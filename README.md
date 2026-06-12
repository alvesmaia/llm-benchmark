# LLM Coding Benchmark

Benchmark próprio para avaliar **LLMs operando como code agents**, inspirado na metodologia do
[Fábio Akita](https://akitaonrails.com/2026/04/24/llm-benchmarks-parte-3-deepseek-kimi-mimo/)
(repo de referência: [`akitaonrails/llm-coding-benchmark`](https://github.com/akitaonrails/llm-coding-benchmark)).

Cada candidato (**harness + modelo**) recebe o **brief de um cenário**, constrói o projeto sozinho via
harness automatizado em **3 fases** (build → validação → git), e é pontuado por uma **rubrica 0–100 por
dimensões** com **painel de 2 juízes**, classificando em tiers **A/B/C/D**. O repositório suporta
**múltiplos cenários de teste** — atualmente **2**, cada um com desafio, rubrica e ranking próprios.

## Cenários de teste

| # | Cenário (`id`) | Desafio | Dimensões | Spec |
|---|---|---|---|---|
| 1 | **ETL CEP Correios** (`cep_etl`) | ETL da base de CEP dos Correios + **3 interfaces** (CLI + API REST + Web) para consultar 1+ CEPs | 9 | [`challenge.md`](benchmark/brief/challenge.md) |
| 2 | **Gestão de Estoque** (`inventory`) | Login + **API REST** + entrada/saída de produtos (cadastro) + **dashboard** de custos/movimentações/revenue, sobre o dataset [`car-sales-report`](https://www.kaggle.com/datasets/missionjee/car-sales-report) | 11 | [`challenge.md`](benchmark/inventory/brief/challenge.md) |

Cada cenário tem **dimensões e ranking próprios**. Selecione com `uv run bench run --scenario <id>`
(`cep_etl` é o default). O 2º cenário foi adicionado porque o ranking do 1º **saturou** (vários
candidatos 96–99/Tier A); dimensões de auth/estoque/dashboard diferenciam melhor os candidatos.

## Ranking: harness + modelo

O ranking é por **candidato = harness (agent) + modelo**, não só por modelo. O mesmo modelo conta como
entradas distintas conforme o harness (ex.: `claude_code-opus` vs `copilot_cli-copilot-opus`), porque o
harness influencia o resultado.

Matriz inicial (em [`benchmark/harness/config.yaml`](benchmark/harness/config.yaml)):

| Harness (agent) | Modelo |
|-----------------|--------|
| Claude Code     | Opus |
| Claude Code     | Sonnet |
| Claude Code     | Haiku |
| GitHub Copilot CLI | Claude Opus |
| GitHub Copilot CLI | Claude Sonnet |
| GitHub Copilot CLI | GPT (codex) |
| opencode | Claude Sonnet |

## Ranking — Cenário 1: ETL CEP Correios

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
- **Subtotal** — soma ponderada das 9 dimensões (0–100, **antes** dos modificadores) — critério de ordenação
- **Score** — Subtotal + modificadores (bônus de performance, penalidades), com teto 100
- **Tier** — faixa do Score: A (80+), B (60–79), C (40–59), D (<40)
- **Tempo** — tempo total de conclusão (soma das 3 fases: build + validação + git)

Dimensões avaliadas (nota 0–100 por dimensão · peso na rubrica):

- **ETL** (peso 18) — correção do ETL/parsing da base DNE (encoding Latin-1, separador `@`, mapeamento de campos, fallback de CEP de localidade)
- **Completude** (peso 13) — completude dos entregáveis obrigatórios (ETL, consulta, CLI, API, Web, testes, README, lint/CI)
- **Interfaces** (peso 14) — as três interfaces de consulta (CLI, API REST e Web) funcionam, aceitam 1+ CEPs, e o projeto roda via `uv run`/`uvx`
- **Persistência** (peso 11) — modelagem do banco: schema, índice por CEP e carga idempotente
- **Testes** (peso 11) — suíte de testes (pytest) cobre ETL/consulta/erros e passa
- **Tratamento de Erros** (peso 9) — tratamento de CEP inválido, CEP não encontrado e base DNE ausente
- **Arquitetura** (peso 8) — arquitetura e organização do código (modularidade, separação de camadas)
- **Produção** (peso 8) — preparação para produção (CI, README, lint/ruff, empacotamento)
- **Git** (peso 8) — interação com Git/GitHub: commits significativos, tag semver e push

- **Custo (US$)** — custo-equivalente estimado das fases (referência; o consumo conta no plano)
- **Diverg.** — dimensões com divergência grande entre os juízes (sinalizadas p/ revisão)

| # | Harness | Modelo | Thinking | Subtotal | Score | Tier | Tempo | ETL | Completude | Interfaces | Persistência | Testes | Tratamento de Erros | Arquitetura | Produção | Git | Custo (US$) | Diverg. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude_code | Opus 4.7 · 1M | xhigh | **99.6** | 100.0 | A | — | 100 | 100 | 100 | 100 | 100 | 100 | 95 | 100 | 100 | 4.412 | — |
| 2 | claude_code | Opus 4.8 · 1M | xhigh | **99.2** | 100.0 | A | — | 100 | 100 | 100 | 100 | 99 | 100 | 95 | 99 | 97 | 3.956 | — |
| 3 | claude_code | Fable 5 · 1M | high | **98.3** | 100.0 | A | 9m 53s | 99 | 100 | 98 | 98 | 98 | 99 | 94 | 98 | 98 | 6.176 | — |
| 4 | opencode | Sonnet 4.6 · 1M | xhigh | **97.6** | 100.0 | A | 14m 58s | 98 | 100 | 98 | 97 | 97 | 99 | 91 | 97 | 97 | 2.353 | — |
| 5 | codex_cli | GPT-5.4 (Codex) | medium | **97.5** | 100.0 | A | 9m 55s | 98 | 100 | 98 | 96 | 97 | 98 | 94 | 98 | 95 | — | — |
| 6 | copilot_cli | Sonnet 4.6 · 1M | xhigh | **96.7** | 99.7 | A | 13m 11s | 98 | 100 | 98 | 96 | 96 | 98 | 88 | 96 | 96 | — | — |
| 7 | claude_code | Sonnet 4.6 | xhigh | **96.5** | 99.5 | A | — | 98 | 100 | 98 | 95 | 97 | 98 | 88 | 94 | 96 | 3.100 | — |
| 8 | claude_code | Haiku 4.5 | xhigh | **75.2** | 78.2 | B | 14m 42s | 52 | 100 | 57 | 97 | 91 | 32 | 73 | 95 | 97 | 1.440 | — |

## Modificadores aplicados

- **claude_code-claude-opus-4-7**: load_performance_bonus (+3)
- **claude_code-claude-opus-4-8**: load_performance_bonus (+3)
- **claude_code-claude-fable-5**: load_performance_bonus (+3)
- **opencode-github-copilot/claude-sonnet-4.6**: load_performance_bonus (+3)
- **codex_cli-gpt-5.4**: load_performance_bonus (+3)
- **copilot_cli-claude-sonnet-4.6**: load_performance_bonus (+3)
- **claude_code-sonnet**: load_performance_bonus (+3)
- **claude_code-claude-haiku-4-5-20251001**: load_performance_bonus (+3)
<!-- LEADERBOARD:END -->

## Ranking — Cenário 2: Gestão de Estoque (car-sales)

> Seção **gerada** por `uv run bench run --scenario inventory` (ou `bench report --scenario inventory`).
> Ver também [`results/inventory/leaderboard.md`](results/inventory/leaderboard.md).

Rubrica de **11 dimensões**, com maior peso em **Lógica de Estoque, Autenticação, Dashboard e API REST**.

<!-- LEADERBOARD-INVENTORY:START -->

Ranking por **candidato = harness (agent) + modelo**. O mesmo modelo aparece como
entradas distintas conforme o harness (o harness influencia o resultado).

Ordenado por **Subtotal** (soma ponderada 0–100 pré-modificadores), que diferencia melhor
que o Score final — este satura no teto 100 e inclui bônus/penalidades.

_Nenhum resultado ainda. Rode `uv run bench run` e depois `uv run bench report`._
<!-- LEADERBOARD-INVENTORY:END -->

## Como o custo (US$) é calculado

A coluna **Custo (US$)** do ranking é o **custo-equivalente em API** reportado pelo próprio CLI do
agente (campo `total_cost_usd` do Claude Code), **somado pelas 3 fases** (build + validação + git):

```
custo_fase = (input_tokens        × preço_input)
           + (output_tokens       × preço_output)
           + (cache_write_tokens  × preço_cache_write)
           + (cache_read_tokens   × preço_cache_read)      # preços por token = US$/1M ÷ 1.000.000

custo_total = Σ custo_fase  (build, validação, git)
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
  **write = 1,25×** (TTL 5 min) ou **2× (TTL 1 h)**; **read = 0,1×**. O Claude Code usa cache de **1 h**,
  então `cache write = 2× input` (Opus 10,00; Sonnet 6,00) e `cache read = 0,1× input` (Opus 0,50; Sonnet 0,30).
- O **Codex (GPT-5.4)** roda via **conta ChatGPT** e **não reporta** `total_cost_usd` — por isso o custo
  aparece como `—` no ranking (o consumo conta no plano ChatGPT).
- Preços de referência da Anthropic (jun/2026); o cache de cada fase reduz muito o custo das fases
  seguintes (a fase 1 escreve o cache; as fases 2 e 3 leem a 0,1×).

## Como funciona

1. **Fase 1 (build):** o agente recebe o brief e constrói a aplicação, headless, num diretório isolado.
2. **Fase 2 (validação):** continua a mesma sessão para dar boot, rodar testes e lint, e corrigir falhas.
3. **Fase 3 (git):** o agente commita, cria **tag semver** e faz **push** para o branch do modelo.
4. **Checagens objetivas (por cenário):** o harness roda `pytest`, `ruff`, carga da fixture, execução via
   `uvx`/`uv run` e a bateria de verdades do cenário (`expected_queries.json` no CEP;
   `expected_metrics.json`, auth e regras de estoque no Estoque).
5. **Painel de 2 juízes:** Claude Opus + Copilot GPT pontuam a rubrica de forma independente; a nota de cada
   dimensão é a **média** das duas (reduz viés; divergências grandes são sinalizadas).
6. **Score + leaderboard:** combina objetivo + juízes ponderado pela rubrica, aplica modificadores e tier.
   Opcionalmente, **exporta um ZIP por candidato** (app + prompt do juiz) para reavaliação por juiz externo.

## Isolamento Git

Cada projeto gerado em `runs/<slug>/app/` é um **repo git independente** (`.git` próprio). Como `runs/` está
no `.gitignore` do repo raiz, esse `.git` aninhado **não interfere** no benchmark. O harness configura o
`origin` para o **mesmo remoto GitHub**, empurrando para `run/<slug>` com **tags namespaced** `<slug>/vX.Y.Z`.

## Uso

```bash
# instalar deps do harness (uv gerencia o Python)
uv sync

# self-test do harness contra a fixture sintética (não precisa do DNE real nem de agentes)
uv run bench selftest

# rodar a matriz completa (dirige claude/copilot via assinatura mensal, modo headless)
uv run bench run

# rodar um candidato específico
uv run bench run --only claude_code-sonnet

# rodar o 2º cenário (Gestão de Estoque) — vale --scenario em run/report/selftest/rescore
uv run bench selftest --scenario inventory
uv run bench run --scenario inventory

# pontuar e gerar o leaderboard (do cenário escolhido)
uv run bench report                      # cep_etl (default)
uv run bench report --scenario inventory

# exportar, por candidato, um ZIP (app + prompt do juiz) p/ reavaliação por juiz externo
uv run bench export <slug> --scenario inventory

# avaliar manualmente um resultado em um único comando (sobe Web + API)
uv run bench serve claude_code-opus
# ...ou standalone, direto no projeto gerado:
uvx --from runs/claude_code-opus/app cep-etl serve
```

## Datasets (por cenário)

Os datasets reais ficam **offline** (gitignored); cada cenário usa uma **fixture sintética** versionada para
CI/auto-teste, e o caminho do dataset real é servido aos agentes via env.

- **Cenário 1 — DNE Correios** (`cep_etl`): base oficial é **proprietária**, nunca versionada. Configure
  `dne_path` em `config.yaml` apontando para a pasta com os `LOG_*.TXT`; o padrão aponta para a fixture
  `benchmark/fixtures/dne_sample/` (formato `@`/Latin-1). Servido via `DNE_PATH`.
- **Cenário 2 — car-sales** (`inventory`): mantenha o CSV do Kaggle offline; aponte
  `scenarios.inventory.dataset` no `config.yaml` (padrão: fixture `benchmark/inventory/fixtures/`).
  Servido via `DATASET_PATH`.

## Estrutura

Ver o plano de implementação e [`docs/methodology.md`](docs/methodology.md) para a justificativa dos pesos
e a adaptação da metodologia do Akita.
