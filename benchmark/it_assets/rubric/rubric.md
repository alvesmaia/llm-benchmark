# Rubrica de Avaliação — Gestão de Ativos de TI (0–100, 12 dimensões)

Benchmark em **3 fases com mudança de direção + perturbação** (dashboard Streamlit → refatoração para
FastAPI/SQLite/Jinja2/JWT/RBAC → correção após o harness mutar a base). Pontua-se o **estado final**
(pós-Fase 3). Pesos numéricos explícitos somando 100.

```
score = Σ (peso_i × nota_i / 100) + modificadores      # depois clampeado em [0, 100]
```

`nota_i` (0–100) por dimensão = combinação da checagem objetiva (quando há) com a **média do painel de juízes**.

## Dimensões e pesos

| # | Dimensão | Peso | Fonte da nota |
|---|----------|-----:|---------------|
| 1 | **Refatoração (pivô)** ★ — qualidade da virada Streamlit → FastAPI/SQLite/Jinja2/JWT/RBAC; reaproveitamento e camadas | 13 | juízes |
| 2 | **Resiliência** ★ — recuperou-se da perturbação da base (testes e boot voltam a passar sobre os dados mutados) | 12 | objetivo (pós-Fase 3) + juízes |
| 3 | **E2E (usuário real)** ★ — um agente percorre a UI via Playwright: login, dashboard, ação restrita bloqueada | 11 | objetivo (veredito Playwright/Sonnet) |
| 4 | **Autenticação JWT** ★ — `POST /auth/login` 200/401; rotas protegidas exigem Bearer (sem → 401) | 10 | objetivo (login/proteção) + juízes |
| 5 | **RBAC** ★ — ≥2 papéis; ação restrita negada com 403 ao papel sem permissão | 10 | objetivo (403) + juízes |
| 6 | **Dashboard** — métricas úteis de movimentação coerentes com a base | 9 | objetivo + juízes |
| 7 | **Persistência** — SQLite, schema/índices, carga a partir da base | 8 | objetivo + juízes |
| 8 | **Testes** — cobertura medida (alvo **oculto**); testes passam | 8 | objetivo (cobertura) + juízes |
| 9 | **API/Web** — endpoints REST + telas Jinja2 respondem | 7 | objetivo + juízes |
| 10 | **Execução `uvx`** ★ — um único comando sobe a app lendo o `.env` versionado | 6 | objetivo (boot via uvx) + juízes |
| 11 | **Ingestão** — leitura/parse da base de movimentações | 4 | objetivo + juízes |
| 12 | **Produção** — README, lint (ruff), empacotamento uv/uvx | 2 | objetivo + juízes |
| | **Total** | **100** | |

★ = dimensões diferenciadoras (trabalho em etapas + gerenciamento de contexto).

## Modificadores

| Modificador | Valor | Quando aplica |
|-------------|------:|---------------|
| Dependência/API alucinada | **−10** | biblioteca/pacote/API inexistente que quebre instalação ou import |
| Não dá boot | **−5** | a app não sobe / não responde no healthcheck via `uvx` |
| Performance de carga | **+3** | carga da base de teste abaixo do limiar (`load_time_threshold_seconds`) |

## Tiers

| Tier | Faixa | Leitura |
|------|-------|---------|
| **A** | 80–100 | Pronto para produção (patch < 30 min) |
| **B** | 60–79  | 1–2 h de ajustes; arquitetura sólida com lacunas menores |
| **C** | 40–59  | Retrabalho grande |
| **D** | < 40   | Quebrado / incompleto |

## Sub-critérios por dimensão (guia para os juízes)

Âncoras: **0–20** ausente/quebrado · **40** falhas sérias · **60** funcional com lacunas · **80** sólido · **100** exemplar.

1. **Refatoração:** a virada de stack foi feita reaproveitando o código do dashboard, com camadas coesas
   (persistência/ingestão/domínio/auth/transporte)? A app final é organizada, não um recomeço descartável?
2. **Resiliência:** após a base ser mutada (campos nulos, ação fora do domínio, valor negativo, data em
   formato alternativo, id duplicado), os testes e o boot voltam a passar? A ingestão/validação ficou robusta?
3. **E2E:** a UI funciona como um usuário real esperaria — login do admin, dashboard/listagem renderizam,
   e a ação restrita é bloqueada para o papel sem permissão?
4. **Autenticação JWT:** login válido→token, inválido→401? rotas protegidas exigem Bearer (401/403 sem)?
5. **RBAC:** há ≥2 papéis com permissões distintas? a ação de escrita/admin é negada (403) ao papel sem permissão?
6. **Dashboard:** métricas de movimentação úteis e coerentes com a base (por status/local/colaborador/tempo)?
7. **Persistência:** schema sensato, índices/uniqueness, SQLite populado a partir da base?
8. **Testes:** cobrem login/RBAC/persistência/ingestão? passam? cobertura razoável (o alvo não é revelado)?
9. **API/Web:** endpoints REST corretos e telas Jinja2 que respondem HTML?
10. **Execução `uvx`:** um único `uvx --from . it-assets serve` sobe a app lendo o `.env` versionado?
11. **Ingestão:** lê e parseia a base de movimentações corretamente?
12. **Produção:** README com o comando único, ruff configurado, empacotamento uv/uvx?
