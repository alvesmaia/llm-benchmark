# inv-etl

Gestão de Estoque a partir de um **relatório de vendas** (schema Kaggle *car-sales-report*), com
**API REST**, **dashboard** e **Web com login**.

> Implementação de referência (sample) usada pelo harness de benchmark para auto-teste.

## Requisitos

- [uv](https://docs.astral.sh/uv/)
- Um CSV de vendas no schema car-sales (`Car_id, Date, ..., Company, Model, ..., Price ($), ...,
  Dealer_Region`). Aponte `DATASET_PATH` para ele.

## Carga (ETL / import)

```bash
export DATASET_PATH=/caminho/car_sales.csv
export DB_PATH=inventory.db
export ADMIN_USER=admin
export ADMIN_PASSWORD=admin123
uv run inv-etl import
```

Cada linha do CSV é uma **venda** (saída). O produto é o par `(Company, Model)`. A importação é
**idempotente** (rodar de novo não duplica). Convenção de custo: `unit_cost = floor(0.8 * Price)`.

## Uso

### API REST + Web

```bash
uv run inv-etl serve --host 127.0.0.1 --port 8000
# ...ou em um único comando, sem instalar:
uvx --from . inv-etl serve
```

- Web: <http://127.0.0.1:8000/> — formulário de **login** (usuário/senha).
- `POST /auth/login` `{username, password}` → `{token}` (401 se inválido).
- `GET /api/products` — lista de produtos (leitura pública).
- `POST /api/products` `{company, model, unit_cost}` — **protegida** (Bearer token).
- `POST /api/movements` `{product_id, type:"in"|"out", qty, unit_price?}` — **protegida**; `out`
  maior que o estoque retorna **400** (estoque nunca negativo).
- `GET /api/dashboard` — `{revenue, cost, profit, units_sold, movements, by_company, by_region}`.

Rotas de escrita exigem header `Authorization: Bearer <token>`.

## Desenvolvimento

```bash
uv run ruff check .
uv run pytest -q
```
