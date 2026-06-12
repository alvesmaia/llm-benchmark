# CEP ETL — eDNE Básico dos Correios

Aplicação Python para ETL da base de CEP dos Correios (eDNE Básico) com consulta por CLI, API REST e interface web.

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/) instalado
- Variável de ambiente `DNE_PATH` apontando para a pasta com os arquivos `LOG_*.TXT` do eDNE Básico

## Instalação rápida (uv)

```bash
uv sync
```

## Carga dos dados (ETL)

```bash
# Usando uv run (instala dependências automaticamente):
DNE_PATH=/caminho/para/dne uv run cep-etl load

# Ou definindo também o banco de dados:
DNE_PATH=/caminho/para/dne DB_PATH=/caminho/cep.db uv run cep-etl load
```

O ETL é **idempotente**: pode ser executado múltiplas vezes sem duplicar dados.

## Uso das três interfaces

### 1. CLI

```bash
# Consultar um CEP:
uv run cep-etl query 01001-000

# Consultar múltiplos CEPs:
uv run cep-etl query 01001000 20040002 13012100

# Saída JSON:
uv run cep-etl query --json 01001-000 20040002

# Iniciar servidor web:
uv run cep-etl serve
uv run cep-etl serve --host 0.0.0.0 --port 8080
```

### 2. API REST

Após iniciar o servidor (`cep-etl serve`):

```bash
# Consulta individual:
curl http://localhost:8000/cep/01001-000

# Consulta em lote:
curl -X POST http://localhost:8000/ceps \
  -H "Content-Type: application/json" \
  -d '{"ceps": ["01001000", "20040002"]}'
```

Documentação interativa: http://localhost:8000/docs

### 3. Interface Web

Acesse http://localhost:8000 no navegador, informe um ou mais CEPs (separados por vírgula ou quebra de linha) e clique em **Consultar**.

## Execução standalone (uvx)

```bash
# Carga + servidor em um único fluxo:
DNE_PATH=/caminho/dne uv run cep-etl load && uv run cep-etl serve

# Via uvx:
DNE_PATH=/caminho/dne uvx --from . cep-etl load
uvx --from . cep-etl serve
```

## Variáveis de ambiente

| Variável       | Descrição                                      | Padrão    |
|----------------|------------------------------------------------|-----------|
| `DNE_PATH`     | Pasta com os arquivos `LOG_*.TXT` do eDNE      | (obrigatório para `load`) |
| `DB_PATH`      | Caminho do banco SQLite                        | `cep.db`  |
| `DATABASE_URL` | URL do PostgreSQL (ex: `postgresql://...`)     | (opcional) |

## Testes

```bash
uv run pytest
uv run pytest -v
```

## Lint

```bash
uv run ruff check src tests
uv run ruff format --check src tests
```

## Comportamento de fallback

Se um CEP não estiver cadastrado como logradouro específico, a consulta tenta retornar o **CEP de localidade** (município) correspondente. Se também não houver, retorna um erro claro sem quebrar a consulta dos demais CEPs do lote.

## Schema do banco

- `localidade` — municípios/localidades (indexed por `cep`)
- `bairro` — bairros (FK para `localidade`)
- `logradouro` — logradouros com CEP específico (indexed por `cep`)
