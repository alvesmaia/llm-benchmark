# Checagens objetivas e como mapeiam na rubrica

O harness (`checks.py`, `gitcheck.py`) roda verificações determinísticas sobre o projeto gerado **sem
envolver o agente**. Cada checagem produz um valor 0–100 que entra na nota da dimensão correspondente.

## Combinação objetivo × juízes por dimensão

Para dimensões **mistas**, a nota final da dimensão é:

```
nota_dim = round(peso_obj × nota_objetiva + peso_juiz × media_juizes)
```

| # | Dimensão | peso_obj | peso_juiz |
|---|----------|---------:|----------:|
| 1 | ETL/parsing | 0.7 | 0.3 |
| 2 | Completude | 1.0 | 0.0 |
| 3 | Interfaces | 0.6 | 0.4 |
| 4 | Persistência | 0.5 | 0.5 |
| 5 | Testes | 0.6 | 0.4 |
| 6 | Erros | 0.7 | 0.3 |
| 7 | Arquitetura | 0.0 | 1.0 |
| 8 | Produção | 0.6 | 0.4 |
| 9 | Git/GitHub | 0.7 | 0.3 |

`media_juizes` = média aritmética das notas dos juízes daquela dimensão (ver `judge.py`).

## Checagens objetivas (checks.py)

| id | dimensão | descrição | nota |
|----|----------|-----------|------|
| `files_present` | 2 | presença dos 9 entregáveis (pyproject, ETL, consulta, CLI, app, templates, testes, README, ruff/CI) | % presentes |
| `etl_load` | 1 | `cep-etl load` roda contra a fixture sem erro | 100/0 |
| `expected_queries` | 1 | cada CEP de `expected_queries.json` retorna o endereço esperado (via CLI `--json`) | % corretos |
| `cli_multi` | 3 | `cep-etl query` aceita 2+ CEPs num comando | 100/0 |
| `api_get` | 3 | `GET /cep/{cep}` retorna 200 + JSON correto | 100/0 |
| `api_post_batch` | 3 | `POST /ceps` em lote retorna todos | 100/0 |
| `web_form` | 3 | `GET /` retorna HTML com formulário | 100/0 |
| `uvx_run` | 3 | `uvx --from <app> cep-etl --help` executa | 100/0 |
| `idempotent` | 4 | rodar `load` 2x não altera a contagem de registros | 100/0 |
| `has_index` | 4 | existe índice por CEP no schema (inspeção do SQLite) | 100/0 |
| `pytest` | 5 | suíte do projeto passa | % testes passando |
| `err_invalid` | 6 | CEP inválido tratado (sem stack trace cru / erro acionável) | 100/0 |
| `err_notfound` | 6 | CEP inexistente tratado sem quebrar o lote | 100/0 |
| `err_no_dne` | 6 | `load` sem `DNE_PATH`/arquivos dá mensagem acionável | 100/0 |
| `ruff_ok` | 8 | `ruff check` sem erros (warnings não zeram) | 100/parcial |
| `ci_present` | 8 | workflow de CI presente rodando lint+testes | 100/0 |
| `readme_quality` | 8 | README com seção de carga e de uso | 100/0 |

Mapeamento dos modificadores também é objetivo:
- `hallucinated_dependency` (−10): `uv sync`/import falha por pacote inexistente, ou import de módulo
  notoriamente inexistente detectado.
- `no_boot` (−5): `cep-etl serve` não responde no healthcheck.
- `load_performance_bonus` (+3): tempo de `etl_load` < `load_time_threshold_seconds`.

## Checagens de git (gitcheck.py) — dimensão 9

| id | descrição | nota |
|----|-----------|------|
| `commit_count` | ≥ 2 commits → cheio; 1 commit → parcial; 0 → zero | escala |
| `msg_quality` | proporção de mensagens "significativas" (descartando wip/update/asdf/.); bônus se Conventional Commits | % |
| `semver_tag` | existe tag no formato `vX.Y.Z` (regex SemVer) | 100/0 |
| `push_ok` | branch `run/<slug>` presente no remoto (quando `push_enabled`) | 100/0/N/A |

Quando `push_enabled=false`, `push_ok` é N/A e não penaliza (peso redistribuído nas demais de git).
