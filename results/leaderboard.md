# Leaderboard — Benchmark ETL CEP

Ranking por **candidato = harness (agent) + modelo**. O mesmo modelo aparece como
entradas distintas conforme o harness (o harness influencia o resultado).

Ordenado por **Subtotal** (soma ponderada 0–100 pré-modificadores), que diferencia melhor
que o Score final — este satura no teto 100 e inclui bônus/penalidades.

### Legenda das colunas

- **#** — posição no ranking (ordenado pelo Subtotal)
- **Harness** — o code agent que dirigiu o modelo (ex.: `claude_code`, `copilot_cli`)
- **Modelo** — modelo avaliado; tag `· 1M` quando rodou em contexto de 1M
- **Thinking** — esforço de raciocínio usado (Claude Code: `xhigh`, o default do harness; Codex/Copilot GPT: `medium`)
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
