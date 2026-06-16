# Leaderboard — Benchmark Gestão de Ativos de TI (3 fases)

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
