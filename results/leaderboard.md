# Leaderboard — Benchmark ETL CEP

Ranking por **candidato = harness (agent) + modelo**. O mesmo modelo aparece como
entradas distintas conforme o harness (o harness influencia o resultado).

Ordenado por **Subtotal** (soma ponderada 0–100 pré-modificadores), que diferencia melhor
que o Score final — este satura no teto 100 e inclui bônus/penalidades.

| # | Harness | Modelo | Subtotal | Score | Tier | ETL | Compl. | Interf. | Persist. | Testes | Erros | Arquit. | Prod. | Git | Custo (US$) | Diverg. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude_code | Opus 4.7 · 1M | **99.6** | 100.0 | A | 100 | 100 | 100 | 100 | 100 | 100 | 95 | 100 | 100 | 4.412 | — |
| 2 | claude_code | Opus 4.8 · 1M | **99.2** | 100.0 | A | 100 | 100 | 100 | 100 | 99 | 100 | 95 | 99 | 97 | 3.956 | — |
| 3 | claude_code | Sonnet 4.6 | **96.5** | 99.5 | A | 98 | 100 | 98 | 95 | 97 | 98 | 88 | 94 | 96 | 3.100 | — |

## Modificadores aplicados

- **claude_code-claude-opus-4-7**: load_performance_bonus (+3)
- **claude_code-claude-opus-4-8**: load_performance_bonus (+3)
- **claude_code-sonnet**: load_performance_bonus (+3)
