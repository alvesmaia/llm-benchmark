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
- **Diverg.** — dimensões com divergência grande entre os juízes (sinalizadas p/ revisão)

| # | Harness | Modelo | Thinking | Subtotal | Score | Tier | Tempo | Refatoração | Resiliência | E2E | Auth JWT | RBAC | Dashboard | Persistência | Testes | API/Web | Execução uvx | Ingestão | Produção | Tokens In | Tokens Out | Cache | Interações | Custo (US$) | Cobertura (%) | Diverg. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude_code | Sonnet 4.6 | xhigh | **91.7** | 94.7 | A | 31m 15s | 85 | 98 | 100 | 98 | 98 | 80 | 94 | 97 | 59 | 98 | 97 | 96 | 98 | 102 033 | 7 835 099 | — | 5.397 | 93 | — |

## Modificadores aplicados

- **claude_code-sonnet**: load_performance_bonus (+3)
