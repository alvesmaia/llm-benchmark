# Rubrica de Avaliação — Gestão de Estoque (0–100, 11 dimensões)

Pesos numéricos explícitos somando 100. O **score final** é a soma ponderada das dimensões, cada uma
normalizada de 0 a 100% do seu peso, somada aos **modificadores**.

```
score = Σ (peso_i × nota_i / 100) + modificadores      # depois clampeado em [0, 100]
```

`nota_i` (0–100) por dimensão = combinação da checagem objetiva (quando há) com a **média do painel de juízes**.

## Dimensões e pesos

| # | Dimensão | Peso | Fonte da nota |
|---|----------|-----:|---------------|
| 1 | **Lógica de Estoque** — entradas/saídas atualizam o saldo; estoque nunca negativo (saída > saldo → 400); CRUD de produto | 16 | objetivo (in/out, 400) + juízes |
| 2 | **Autenticação** — senha em HASH (nunca texto plano); login 200/401; rotas de escrita protegidas por Bearer; form de login | 14 | objetivo (login/hash/proteção) + juízes |
| 3 | **Dashboard** — revenue/cost/profit/units_sold/movements + by_company/by_region coerentes com o dataset | 14 | objetivo (métricas esperadas) + juízes |
| 4 | **API REST** — GET/POST produtos, POST movimentações, GET dashboard; execução via uvx/uv run | 12 | objetivo (smoke API/uvx) + juízes |
| 5 | **Ingestão (ETL)** — upsert de produtos por (Company, Model); 1 movimentação OUT por venda; idempotente | 10 | objetivo (import) + juízes |
| 6 | **Persistência** — schema, índices/uniqueness, carga idempotente | 10 | objetivo (idempotência/índice) + juízes (modelagem) |
| 7 | **Testes** — cobrem import/auth/estoque/dashboard; passam | 9 | objetivo (pytest) + juízes (relevância) |
| 8 | **Tratamento de Erros** — dataset ausente, payloads inválidos, regras de estoque violadas | 6 | objetivo (casos) + juízes |
| 9 | **Arquitetura** — camadas (db/etl/auth/inventory/api/web/cli), coesão, clareza | 5 | juízes |
| 10 | **Produção** — README, lint (ruff), CI (lint+testes), empacotamento uv/uvx | 2 | objetivo (ruff/CI/README) + juízes |
| 11 | **Git/GitHub** — commits significativos, tag semver válida, push | 2 | objetivo (gitcheck) + juízes (qualidade das mensagens) |
| | **Total** | **100** | |

## Modificadores

| Modificador | Valor | Quando aplica |
|-------------|------:|---------------|
| Dependência/API alucinada | **−10** | biblioteca/pacote/API inexistente que quebre instalação ou import |
| Não dá boot | **−5** | `inv-etl serve` não sobe / não responde no healthcheck |
| Performance de carga | **+3** | importação do dataset de teste abaixo do limiar (`load_time_threshold_seconds`) |

## Tiers

| Tier | Faixa | Leitura |
|------|-------|---------|
| **A** | 80–100 | Pronto para produção (patch < 30 min) |
| **B** | 60–79  | 1–2 h de ajustes; arquitetura sólida com lacunas menores |
| **C** | 40–59  | Retrabalho grande |
| **D** | < 40   | Quebrado / incompleto |

## Sub-critérios por dimensão (guia para os juízes)

Âncoras: **0–20** ausente/quebrado · **40** falhas sérias · **60** funcional com lacunas · **80** sólido · **100** exemplar.

1. **Lógica de Estoque:** `in` soma e `out` subtrai do saldo? saída maior que o saldo retorna 400 (nunca negativo)?
   produto identificado por (Company, Model)? CRUD funciona?
2. **Autenticação:** senha armazenada em hash (pbkdf2/passlib), nunca em texto plano? login válido→token,
   inválido→401? rotas de escrita exigem Bearer token (401/403 sem)? Web tem formulário de login?
3. **Dashboard:** revenue = soma dos unit_price das saídas? cost/profit coerentes com a convenção `floor(0.8*price)`?
   units_sold/movements corretos? by_company/by_region batem com o dataset?
4. **API REST:** endpoints corretos e com status codes adequados? roda via `uv run` e `uvx`?
5. **Ingestão:** lê o schema car-sales? upsert de produtos? 1 OUT por venda? import idempotente (2x não duplica)?
6. **Persistência:** schema normalizado e sensato? índices/uniqueness? rodar o import 2x não duplica?
7. **Testes:** cobrem import, auth, estoque (in/out + saldo), dashboard? passam? asserts relevantes?
8. **Erros:** dataset ausente com mensagem útil? payloads inválidos tratados? saída além do saldo retorna 400?
9. **Arquitetura:** camadas separadas (persistência/ingestão/domínio/auth/transporte)? acoplamento baixo? nomes claros?
10. **Produção:** roda via `uvx`/`uv run`? README com import e uso? ruff configurado? CI roda lint+testes?
11. **Git:** commits com mensagens significativas (não "wip"/"update")? Conventional Commits? tag semver válida? push OK?
