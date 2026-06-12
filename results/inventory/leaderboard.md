# Leaderboard — Benchmark ETL CEP

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

- **Lógica de Estoque** (peso 16) — regras de estoque: entradas/saídas (in/out) atualizam o saldo, estoque nunca fica negativo (saída > saldo → 400), CRUD de produto por (Company, Model)
- **Autenticação** (peso 14) — autenticação: senha em HASH (nunca texto plano), login válido/inválido (200/401), rotas de escrita protegidas por Bearer token, formulário de login na Web
- **Dashboard** (peso 14) — dashboard de métricas: revenue/cost/profit/units_sold/movements e agregações by_company/by_region coerentes com o dataset importado
- **API REST** (peso 12) — API REST (FastAPI): GET/POST de produtos, POST de movimentações, GET /api/dashboard, execução via uvx/uv run
- **Ingestão** (peso 10) — ETL de ingestão do CSV de vendas (schema car-sales): upsert de produtos e uma movimentação OUT por venda, idempotente
- **Persistência** (peso 10) — modelagem do banco: schema, índices, uniqueness e carga idempotente
- **Testes** (peso 9) — suíte de testes (pytest) cobre import/auth/estoque/dashboard e passa
- **Tratamento de Erros** (peso 6) — tratamento de dataset ausente, payloads inválidos e regras de estoque violadas, sem stack trace cru
- **Arquitetura** (peso 5) — arquitetura em camadas (db/etl/auth/inventory/api/web/cli), coesão e clareza
- **Produção** (peso 2) — preparação para produção: README, lint (ruff), CI (lint+testes), empacotamento uv/uvx
- **Git** (peso 2) — interação com Git/GitHub: commits significativos, tag semver e push

- **Custo (US$)** — custo-equivalente estimado das fases (referência; o consumo conta no plano)
- **Diverg.** — dimensões com divergência grande entre os juízes (sinalizadas p/ revisão)

| # | Harness | Modelo | Thinking | Subtotal | Score | Tier | Tempo | Lógica de Estoque | Autenticação | Dashboard | API REST | Ingestão | Persistência | Testes | Tratamento de Erros | Arquitetura | Produção | Git | Custo (US$) | Diverg. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude_code | Opus 4.7 · 1M | medium | **99.7** | 100.0 | A | 5m 48s | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 98 | 95 | 100 | 100 | 2.809 | — |
| 2 | copilot_cli | Opus 4.7 · 1M | medium | **98.4** | 100.0 | A | 9m 9s | 99 | 98 | 99 | 99 | 100 | 98 | 98 | 98 | 92 | 99 | 99 | — | — |

## Modificadores aplicados

- **claude_code-claude-opus-4-7**: load_performance_bonus (+3)
- **copilot_cli-claude-opus-4.7**: load_performance_bonus (+3)
