# Metodologia

Este benchmark adapta a metodologia do Fábio Akita
([série "LLM Benchmarks"](https://akitaonrails.com/2026/04/24/llm-benchmarks-parte-3-deepseek-kimi-mimo/),
repo [`akitaonrails/llm-coding-benchmark`](https://github.com/akitaonrails/llm-coding-benchmark))
para um desafio em **Python avaliado em etapas**: um cenário único **`it_assets`** (gestão de movimentação
de **ativos de TI**) construído em **3 fases que continuam a mesma sessão**, com foco no que mais diferencia
as ferramentas hoje — **gerenciamento de contexto** sob mudança de direção.

## O que viemos do Akita

- **Mesmo brief para todos os modelos**, construção autônoma via harness headless.
- **Execução em fases** (ele usa 2; nós usamos 3 — ver abaixo).
- **Rubrica holística 0–100** classificada em **tiers A/B/C/D** com as mesmas faixas e leitura
  ("Tier A = pronto para produção com patch < 30 min", etc.).
- **Penalidade por alucinação** (API/dependência inexistente) e **bônus/penalidade** de boot/carga.
- **Ranking por harness + modelo** (o mesmo modelo conta como entradas distintas conforme o harness, que
  influencia fortemente o resultado — observação também feita pelo Akita).

## O que adaptamos / acrescentamos

### 1. Desafio em 3 fases com pivô + perturbação (gerenciamento de contexto)
O diferencial do benchmark é trabalhar **em etapas que estressam o contexto**, na **mesma sessão** do agente:

- **Fase 1 — Dashboard:** planejar e implementar um **dashboard Streamlit** (Python 3.12 + uv) sobre a base
  fornecida. O modelo **copia** a base (de `DATASET_PATH`) para `data/` no projeto e a usa de lá.
- **Fase 2 — Refatoração (pivô):** refatorar o dashboard numa **aplicação completa** — **FastAPI + SQLite +
  Jinja2**, com **JWT + RBAC**. Troca de stack proposital: testa reaproveitamento e migração limpa.
- **Fase 3 — Perturbação dirigida:** o **harness muta valores** no CSV copiado em `data/` (campos nulos,
  ação fora do domínio, valor negativo, data em formato alternativo, id duplicado) e pede ao modelo para
  **rodar os testes e corrigir**. Mede robustez/depuração.

**Sem fase de git** (diferente do brief Rails do Akita). Pontua-se o **estado final** (pós-Fase 3).

### 2. Base fictícia sem estrutura imposta
A base de movimentação de ativos de TI é **gerada deterministicamente** e fornecida igual para todos; a
**estrutura final da aplicação não é imposta** — só um [contrato mínimo](../benchmark/it_assets/brief/challenge.md)
(console script; `POST /auth/login`; ≥1 rota protegida; ≥1 ação restrita por papel; SQLite a partir da base)
para viabilizar checagens determinísticas. Avalia-se o que o modelo decide entregar.

### 3. Execução por um único comando `uvx`
O resultado deve subir com **um único `uvx`**, carregando automaticamente um **`.env` versionado e
preenchido**. Sem Docker — empacotamento e execução via **uv/uvx**.

### 4. Pesos numéricos explícitos (12 dimensões)
Para **reprodutibilidade**, cada dimensão tem peso explícito (soma 100) — fonte canônica em
[`benchmark/harness/scenarios/it_assets.py`](../benchmark/harness/scenarios/it_assets.py)
(versão humana em [`rubric.md`](../benchmark/it_assets/rubric/rubric.md)). Os **diferenciadores** (maior peso)
são as dimensões ligadas a etapas/contexto: **Refatoração, Resiliência, E2E, Auth JWT, RBAC, Execução uvx**.

### 5. Painel de 2 juízes (anti-viés) + Juiz E2E
- **Painel de 2 juízes** (LLMs) pontua a rubrica de forma independente; a nota de cada dimensão é a **média**.
  Divergências grandes (> 25 pts) são sinalizadas. Cada juiz **não pontua o output do próprio par
  agente/família de modelo** (anti-auto-favorecimento).
- **Juiz E2E ("funciona como usuário"):** um agente **Sonnet** dirige o **browser via Playwright MCP** —
  login, dashboard e tentativa de ação restrita (esperando bloqueio) — e devolve um veredito que vira a nota
  da dimensão **E2E**. Indisponível em headless/cron ⇒ a dimensão cai para fallback sem quebrar o pipeline.

### 6. Checagens objetivas + juízes + cobertura
Dimensões com verdade objetiva (sobe via `uvx`, JWT 200/401, RBAC 403, SQLite populado, testes passam,
recuperação pós-perturbação) são medidas por **checagens determinísticas**; as subjetivas (Refatoração,
Dashboard) ficam com os juízes; a maioria é **mista**. **Cobertura de testes** é exigida e **medida**, mas o
**alvo de % não é revelado** ao candidato (a nota é proporcional, com limiar interno) — avalia-se o que o
modelo entrega por conta própria.

### 7. Tempo e custo detalhado por fase
Mede-se **tempo** e **custo (input / output / cache write / cache read)** **por fase**, expostos no ranking
(quando o CLI do agente reporta; Copilot/Codex não dão dados estruturados → `—`).

## Reprodutibilidade

- A base é uma **fixture sintética** gerada por `_generate.py` (gitignored; só o gerador e um `expected.json`
  mínimo são versionados); `uv run bench selftest` valida o pipeline ponta a ponta sem agentes pagos.
- Pesos, juízes e modificadores ficam versionados (`scenarios/it_assets.py`, `config.yaml`) para auditoria.

## Justificativa dos pesos

| Dimensão | Peso | Por quê |
|----------|-----:|---------|
| Refatoração ★ | 13 | virada Streamlit→FastAPI/SQLite/JWT/RBAC é o teste central de gerenciamento de contexto |
| Resiliência ★ | 12 | recuperar-se da perturbação da base mostra robustez/depuração real |
| E2E ★ | 11 | "funciona como usuário" (Playwright/Sonnet) — valida o produto, não o código |
| Auth JWT ★ | 10 | autenticação correta é pré-requisito de uma aplicação |
| RBAC ★ | 10 | controle de acesso por papéis (403) — segurança verificável |
| Dashboard | 9 | a entrega da Fase 1 (métricas de movimentação) |
| Persistência | 8 | modelagem SQLite, schema/índices, carga |
| Testes | 8 | confiabilidade verificável + **cobertura medida (alvo oculto)** |
| API/Web | 7 | endpoints REST + telas Jinja2 |
| Execução uvx ★ | 6 | um único comando sobe a app lendo o `.env` versionado |
| Ingestão | 4 | leitura/parse da base de movimentações |
| Produção | 2 | README, lint (ruff), empacotamento uv/uvx |

★ = diferenciadores (etapas + gerenciamento de contexto).
