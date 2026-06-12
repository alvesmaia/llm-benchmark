# cep-etl

ETL da base de CEP dos Correios (eDNE Básico) com consulta por **CLI**, **API REST** e **Web**.

> Implementação de referência (sample) usada pelo harness de benchmark para auto-teste.

## Requisitos

- [uv](https://docs.astral.sh/uv/)
- A base DNE: aponte `DNE_PATH` para uma pasta com `LOG_LOCALIDADE.TXT`, `LOG_BAIRRO.TXT` e
  `LOG_LOGRADOURO_<UF>.TXT` (delimitados por `@`, encoding Latin-1).

## Carga (ETL)

```bash
export DNE_PATH=/caminho/da/base/dne
export DB_PATH=cep.db
uv run cep-etl load
```

A carga é **idempotente**: rodar de novo não duplica registros.

## Uso

### CLI

```bash
uv run cep-etl query 01001000 20040002          # um ou mais CEPs
uv run cep-etl query 01001-000 --json           # aceita máscara; saída JSON
```

### API REST + Web

```bash
uv run cep-etl serve --host 127.0.0.1 --port 8000
# ...ou em um único comando, sem instalar:
uvx --from . cep-etl serve
```

- Web: <http://127.0.0.1:8000/> (formulário para 1+ CEPs)
- `GET /cep/{cep}` — consulta um CEP (404 se não encontrado)
- `POST /ceps` — corpo `{"ceps": ["01001000", "20040002"]}` (consulta em lote)

## Desenvolvimento

```bash
uv run ruff check .
uv run pytest -q
```
