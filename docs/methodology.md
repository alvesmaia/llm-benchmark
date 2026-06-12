# Metodologia

Este benchmark adapta a metodologia do Fábio Akita
([série "LLM Benchmarks"](https://akitaonrails.com/2026/04/24/llm-benchmarks-parte-3-deepseek-kimi-mimo/),
repo [`akitaonrails/llm-coding-benchmark`](https://github.com/akitaonrails/llm-coding-benchmark))
para um desafio em **Python**: um **ETL da base de CEP dos Correios** com consulta por **CLI + API + Web**.

## O que viemos do Akita

- **Mesmo brief para todos os modelos**, construção autônoma via harness headless.
- **Execução em fases** (ele usa 2; nós usamos 3 — ver abaixo).
- **Rubrica holística 0–100** classificada em **tiers A/B/C/D** com as mesmas faixas e leitura
  ("Tier A = pronto para produção com patch < 30 min", etc.).
- **Penalidade por alucinação** (API/dependência inexistente), que no método dele distorcia o ranking
  quando o peso da "API correta" era alto demais.

## O que adaptamos / acrescentamos

### 1. Domínio Python/ETL em vez de Rails
As 8 dimensões do Akita (Completude, Correção da API RubyLLM, Testes, Tratamento de erros, Persistência,
Hotwire, Arquitetura, Produção) foram remapeadas para o domínio:

| Akita (Rails/RubyLLM) | Aqui (Python/ETL CEP) |
|-----------------------|------------------------|
| Correção da API RubyLLM | **Correção do ETL / parsing DNE** (encoding Latin-1, separador `@`, campos, fallback) |
| Hotwire (frontend) | **Interfaces CLI + API + Web** + execução `uv`/`uvx` |
| Persistência | **Schema, índice por CEP, carga idempotente** |
| (demais) | mantidas, recontextualizadas |

### 2. Pesos numéricos explícitos
O Akita pontua de forma holística (sem pesos publicados por dimensão). Para **reprodutibilidade**, aqui
cada dimensão tem peso explícito (soma 100) — ver [`benchmark/rubric/rubric.md`](../benchmark/rubric/rubric.md).
A correção do ETL é a dimensão de maior peso (18), análoga ao papel central da "API correta" no Akita,
mas calibrada para não dominar o restante.

### 3. Nona dimensão: interação com Git/GitHub
Avaliamos o agente como engenheiro completo: **commits significativos, mensagens (Conventional Commits),
tag semver e push**. Cada projeto gerado é um repo git independente que faz push para o mesmo remoto em
branch por modelo (`run/<slug>`) com tags namespaced.

### 4. Três fases
- **Fase 1 — build:** construir a aplicação a partir do brief.
- **Fase 2 — validação:** dar boot, rodar testes e lint, corrigir falhas (na mesma sessão).
- **Fase 3 — git:** versionar (commits + tag semver + push).

### 5. Painel de 2 juízes (anti-viés)
Em vez de um único juiz, usamos **Claude Opus + GitHub Copilot (GPT)**. Cada um pontua a rubrica de forma
independente e a nota de cada dimensão é a **média**. Divergências grandes (> 25 pts) são sinalizadas para
revisão manual. Cada juiz **não pontua o output do próprio par agente/modelo** (anti-auto-favorecimento).

### 6. Checagens objetivas + juízes
Dimensões com verdade objetiva (ETL correto, testes passando, idempotência, interfaces respondendo, lint, CI)
são medidas por **checagens determinísticas** do harness; dimensões subjetivas (Arquitetura) ficam com os
juízes. A maioria é **mista**, combinando as duas fontes com pesos em
[`benchmark/rubric/objective_checks.md`](../benchmark/rubric/objective_checks.md).

### 7. Ranking por harness + modelo
O mesmo modelo conta como **entradas distintas** conforme o harness (Claude Code vs Copilot CLI), porque o
harness influencia fortemente o resultado — observação também feita pelo Akita.

### 8. Sem Docker
Diferente do brief Rails do Akita (que exige docker-compose), aqui o empacotamento e a execução são via
**uv/uvx** (`uv run cep-etl ...`, `uvx --from . cep-etl ...`).

## Reprodutibilidade

- A base DNE oficial é **proprietária**; o harness inclui uma **fixture sintética** no formato `@`/Latin-1
  para auto-teste sem o arquivo real (`uv run bench selftest`).
- Pesos, juízes e modificadores ficam versionados (`rubric.py`, `config.yaml`) para auditoria.

## Justificativa dos pesos

| Dimensão | Peso | Por quê |
|----------|-----:|---------|
| ETL/parsing | 18 | núcleo do desafio; erro aqui invalida o produto |
| Completude | 13 | entregar todos os artefatos é pré-requisito (lição do Akita) |
| Interfaces | 14 | três interfaces + execução em um comando são o valor para o usuário |
| Persistência | 11 | modelagem/idempotência/índice definem qualidade dos dados |
| Testes | 11 | confiabilidade verificável |
| Erros | 9 | robustez em entradas reais (CEP inválido/inexistente) |
| Arquitetura | 8 | qualidade estrutural (subjetiva) |
| Produção | 8 | CI/lint/README/empacotamento |
| Git/GitHub | 8 | maturidade de engenharia no fluxo de versionamento |
