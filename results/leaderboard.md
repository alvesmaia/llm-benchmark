# Leaderboard — Benchmark ETL CEP

Ranking por **candidato = harness (agent) + modelo**. O mesmo modelo aparece como
entradas distintas conforme o harness (o harness influencia o resultado).

Ordenado por **Subtotal** (soma ponderada 0–100 pré-modificadores), que diferencia melhor
que o Score final — este satura no teto 100 e inclui bônus/penalidades.

### Legenda das colunas

- **#** — posição no ranking (ordenado pelo Subtotal)
- **Harness** — o code agent que dirigiu o modelo (ex.: `claude_code`, `copilot_cli`)
- **Modelo** — modelo avaliado; tag `· 1M` quando rodou em contexto de 1M
- **Thinking** — modo/esforço de raciocínio do modelo na execução (ex.: `adaptive` no Claude Code, `medium` no Codex)
- **Subtotal** — soma ponderada das 9 dimensões (0–100, **antes** dos modificadores) — critério de ordenação
- **Score** — Subtotal + modificadores (bônus de performance, penalidades), com teto 100
- **Tier** — faixa do Score: A (80+), B (60–79), C (40–59), D (<40)

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

| # | Harness | Modelo | Thinking | Subtotal | Score | Tier | ETL | Completude | Interfaces | Persistência | Testes | Tratamento de Erros | Arquitetura | Produção | Git | Custo (US$) | Diverg. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude_code | Opus 4.7 · 1M | adaptive | **99.6** | 100.0 | A | 100 | 100 | 100 | 100 | 100 | 100 | 95 | 100 | 100 | 4.412 | — |
| 2 | claude_code | Opus 4.8 · 1M | adaptive | **99.2** | 100.0 | A | 100 | 100 | 100 | 100 | 99 | 100 | 95 | 99 | 97 | 3.956 | — |
| 3 | claude_code | Sonnet 4.6 | adaptive | **96.5** | 99.5 | A | 98 | 100 | 98 | 95 | 97 | 98 | 88 | 94 | 96 | 3.100 | — |

## Modificadores aplicados

- **claude_code-claude-opus-4-7**: load_performance_bonus (+3)
- **claude_code-claude-opus-4-8**: load_performance_bonus (+3)
- **claude_code-sonnet**: load_performance_bonus (+3)
