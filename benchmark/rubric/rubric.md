# Rubrica de Avaliação (0–100, 9 dimensões)

Adaptada da metodologia holística de 8 dimensões do Akita para o domínio Python/ETL, com **pesos numéricos
explícitos** e uma 9ª dimensão (Git/GitHub). O **score final** é a soma ponderada das dimensões, cada uma
normalizada de 0 a 100% do seu peso, somada aos **modificadores**.

```
score = Σ (peso_i × nota_i / 100) + modificadores      # depois clampeado em [0, 100]
```

`nota_i` (0–100) por dimensão = combinação da checagem objetiva (quando há) com a **média do painel de juízes**.
Para dimensões mistas, a regra de combinação está em `objective_checks.md`.

## Dimensões e pesos

| # | Dimensão | Peso | Fonte da nota |
|---|----------|-----:|---------------|
| 1 | **Correção do ETL / parsing DNE** — encoding Latin-1, separador `@`, mapeamento de campos, faixas/fallback de CEP | 18 | objetivo (queries esperadas) + juízes |
| 2 | **Completude dos entregáveis** — todos os 11 artefatos obrigatórios presentes | 13 | objetivo (checklist) |
| 3 | **Interfaces CLI + API + Web + execução uv/uvx** — as três funcionam e aceitam 1+ CEPs | 14 | objetivo (smoke CLI/API/uvx) + juízes (Web/UX) |
| 4 | **Persistência de dados** — schema, índice por CEP, carga idempotente | 11 | objetivo (idempotência) + juízes (modelagem) |
| 5 | **Qualidade dos testes** — cobrem ETL, consulta, fallback, erros; passam | 11 | objetivo (pytest) + juízes (relevância) |
| 6 | **Tratamento de erros e validação de CEP** — inválido, não encontrado, DNE ausente | 9 | objetivo (casos) + juízes |
| 7 | **Arquitetura e organização do código** — modularidade, separação de camadas, coesão | 8 | juízes |
| 8 | **Preparação para produção** — CI, README, lint, config, empacotamento uv/uvx | 8 | objetivo (ruff/CI/README/uvx) + juízes |
| 9 | **Interação com Git/GitHub** — commits significativos, mensagens, tag semver válida, push | 8 | objetivo (gitcheck) + juízes (qualidade das mensagens) |
| | **Total** | **100** | |

## Modificadores

| Modificador | Valor | Quando aplica |
|-------------|------:|---------------|
| Dependência/API alucinada | **−10** | biblioteca/pacote/API inexistente que quebre instalação ou import |
| Não dá boot | **−5** | `cep-etl serve` não sobe / não responde no healthcheck |
| Performance de carga | **+3** | carga da base de teste abaixo do limiar (`load_time_threshold_seconds`) |

## Tiers (faixas do Akita)

| Tier | Faixa | Leitura |
|------|-------|---------|
| **A** | 80–100 | Pronto para produção (patch < 30 min) |
| **B** | 60–79  | 1–2 h de ajustes; arquitetura sólida com lacunas menores |
| **C** | 40–59  | Retrabalho grande |
| **D** | < 40   | Quebrado / incompleto |

## Sub-critérios por dimensão (guia para os juízes)

Cada dimensão é pontuada de 0 a 100. Âncoras:

- **0–20:** ausente ou totalmente quebrado.
- **40:** existe mas com falhas sérias.
- **60:** funcional com lacunas.
- **80:** sólido, pequenas ressalvas.
- **100:** exemplar, sem ressalvas.

Detalhes por dimensão:

1. **ETL/parsing:** lê os 3 tipos de arquivo? encoding correto? separador `@`? mapeia campos certos? faz
   fallback para CEP de localidade? consultas de teste retornam o endereço correto?
2. **Completude:** os 11 entregáveis existem e são reais (não stubs vazios)?
3. **Interfaces:** CLI `query` aceita múltiplos CEPs? API `GET`/`POST` corretos? Web tem formulário + tabela?
   roda via `uv run` e `uvx`?
4. **Persistência:** schema normalizado e sensato? índice por CEP? rodar o ETL 2x não duplica?
5. **Testes:** cobrem caminhos felizes e de erro? passam? asserts relevantes (não triviais)?
6. **Erros:** CEP inválido tratado? não encontrado tratado sem quebrar o lote? DNE ausente com mensagem útil?
7. **Arquitetura:** camadas separadas (parsing/persistência/consulta/interfaces)? acoplamento baixo? nomes claros?
8. **Produção:** roda via `uvx`/`uv run`? README com instruções de carga e uso? ruff configurado? CI roda lint+testes?
9. **Git:** commits com mensagens significativas (não "wip"/"update")? Conventional Commits? tag semver válida? push OK?
