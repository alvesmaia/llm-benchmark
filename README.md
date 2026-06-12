# LLM Coding Benchmark — ETL CEP Correios

Benchmark próprio para avaliar **LLMs operando como code agents**, inspirado na metodologia do
[Fábio Akita](https://akitaonrails.com/2026/04/24/llm-benchmarks-parte-3-deepseek-kimi-mimo/)
(repo de referência: [`akitaonrails/llm-coding-benchmark`](https://github.com/akitaonrails/llm-coding-benchmark)).

Cada agente recebe **o mesmo brief**, constrói o projeto sozinho via harness automatizado em **3 fases**
(build → validação → git), e é pontuado por uma **rubrica de 0–100 sobre 9 dimensões**, classificando em
tiers **A/B/C/D**.

## O desafio

Implementar um **ETL da base de CEP dos Correios** em Python, com **três interfaces de consulta**
(CLI + API REST + Web) que permitem consultar **um ou mais CEPs**. Spec completa em
[`benchmark/brief/challenge.md`](benchmark/brief/challenge.md).

## Ranking: harness + modelo

O ranking é por **candidato = harness (agent) + modelo**, não só por modelo. O mesmo modelo conta como
entradas distintas conforme o harness (ex.: `claude_code-opus` vs `copilot_cli-copilot-opus`), porque o
harness influencia o resultado.

Matriz inicial (em [`benchmark/harness/config.yaml`](benchmark/harness/config.yaml)):

| Harness (agent) | Modelo |
|-----------------|--------|
| Claude Code     | Opus |
| Claude Code     | Sonnet |
| GitHub Copilot CLI | Claude Opus |
| GitHub Copilot CLI | GPT (codex) |

## Ranking atual

> Esta seção é **gerada automaticamente** ao final de cada `uv run bench run` (ou `uv run bench report`).
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
- **Subtotal** — soma ponderada das 9 dimensões (0–100, **antes** dos modificadores) — critério de ordenação
- **Score** — Subtotal + modificadores (bônus de performance, penalidades), com teto 100
- **Tier** — faixa do Score: A (80+), B (60–79), C (40–59), D (<40)

Dimensões avaliadas (nota 0–100 por dimensão · peso na rubrica):

- **ETL** (peso 18) — correção do ETL/parsing da base DNE (encoding Latin-1, separador `@`, mapeamento de campos, fallback de CEP de localidade)
- **Compl.** (peso 13) — completude dos entregáveis obrigatórios (ETL, consulta, CLI, API, Web, testes, README, lint/CI)
- **Interf.** (peso 14) — as três interfaces de consulta (CLI, API REST e Web) funcionam, aceitam 1+ CEPs, e o projeto roda via `uv run`/`uvx`
- **Persist.** (peso 11) — modelagem do banco: schema, índice por CEP e carga idempotente
- **Testes** (peso 11) — suíte de testes (pytest) cobre ETL/consulta/erros e passa
- **Erros** (peso 9) — tratamento de CEP inválido, CEP não encontrado e base DNE ausente
- **Arquit.** (peso 8) — arquitetura e organização do código (modularidade, separação de camadas)
- **Prod.** (peso 8) — preparação para produção (CI, README, lint/ruff, empacotamento)
- **Git** (peso 8) — interação com Git/GitHub: commits significativos, tag semver e push

- **Custo (US$)** — custo-equivalente estimado das fases (referência; o consumo conta no plano)
- **Diverg.** — dimensões com divergência grande entre os juízes (sinalizadas p/ revisão)

| # | Harness | Modelo | Subtotal | Score | Tier | ETL | Compl. | Interf. | Persist. | Testes | Erros | Arquit. | Prod. | Git | Custo (US$) | Diverg. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude_code | Opus 4.7 · 1M | **99.6** | 100.0 | A | 100 | 100 | 100 | 100 | 100 | 100 | 95 | 100 | 100 | 4.412 | — |
| 2 | claude_code | Opus 4.8 · 1M | **99.2** | 100.0 | A | 100 | 100 | 100 | 100 | 99 | 100 | 95 | 99 | 97 | 3.956 | — |
| 3 | claude_code | Sonnet 4.6 | **96.5** | 99.5 | A | 98 | 100 | 98 | 95 | 97 | 98 | 88 | 94 | 96 | 3.100 | — |

## Modificadores aplicados

- **claude_code-claude-opus-4-7**: load_performance_bonus (+3)
- **claude_code-claude-opus-4-8**: load_performance_bonus (+3)
- **claude_code-sonnet**: load_performance_bonus (+3)
<!-- LEADERBOARD:END -->

## Como funciona

1. **Fase 1 (build):** o agente recebe o brief e constrói a aplicação, headless, num diretório isolado.
2. **Fase 2 (validação):** continua a mesma sessão para dar boot, rodar testes e lint, e corrigir falhas.
3. **Fase 3 (git):** o agente commita, cria **tag semver** e faz **push** para o branch do modelo.
4. **Checagens objetivas:** o harness roda `pytest`, `ruff`, carga da fixture, execução via
   `uvx`/`uv run` e a bateria de `expected_queries.json`.
5. **Painel de 2 juízes:** Claude Opus + Copilot GPT pontuam a rubrica de forma independente; a nota de cada
   dimensão é a **média** das duas (reduz viés; divergências grandes são sinalizadas).
6. **Score + leaderboard:** combina objetivo + juízes ponderado pela rubrica, aplica modificadores e tier.

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

# pontuar e gerar o leaderboard
uv run bench score
uv run bench report

# avaliar manualmente um resultado em um único comando (sobe Web + API)
uv run bench serve claude_code-opus
# ...ou standalone, direto no projeto gerado:
uvx --from runs/claude_code-opus/app cep-etl serve
```

## Base DNE

A base DNE oficial dos Correios é **proprietária** e nunca é versionada. Configure `dne_path` em
`config.yaml` apontando para a pasta com os arquivos `LOG_*.TXT`. Para CI/auto-teste, o padrão aponta para
`benchmark/fixtures/dne_sample/` (fixture sintética no mesmo formato `@`/Latin-1).

## Estrutura

Ver o plano de implementação e [`docs/methodology.md`](docs/methodology.md) para a justificativa dos pesos
e a adaptação da metodologia do Akita.
