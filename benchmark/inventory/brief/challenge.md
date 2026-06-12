# Desafio: Gestão de Estoque a partir de um relatório de vendas (Python)

Você é um engenheiro de software sênior. Implemente, **sozinho e do zero**, uma aplicação Python completa,
pronta para produção, de **gestão de estoque** alimentada por um **relatório de vendas de carros**
(schema do dataset Kaggle *car-sales-report*). A aplicação expõe **CLI**, **API REST**, um **dashboard**
de métricas e uma **Web com login**. Não peça confirmação: tome as decisões necessárias e entregue o projeto inteiro.

## Dataset de entrada (CSV — schema car-sales-report)

O caminho do CSV é fornecido na variável de ambiente **`DATASET_PATH`**. É um CSV **UTF-8 com cabeçalho**,
com exatamente estas colunas (nesta ordem):

```
Car_id, Date, Customer Name, Gender, Annual Income, Dealer_Name, Company, Model, Engine,
Transmission, Color, Price ($), Dealer_No, Body Style, Phone, Dealer_Region
```

- **Cada linha é UMA venda** (uma **saída**/`out` de estoque, quantidade 1).
- **Produto** = par **(`Company`, `Model`)**.
- `Price ($)` é o preço de venda (inteiro/decimal). `Dealer_Region` é a região da venda.

### Convenção de custo (determinística — para o dashboard)
O **custo unitário** de cada venda importada é `floor(0.8 * Price)`. Assim `cost` e `profit` são
deriváveis do CSV de forma reprodutível.

## Variáveis de ambiente fornecidas pelo harness
- `DATASET_PATH` — caminho do CSV de vendas.
- `DB_PATH` — caminho do SQLite (default `inventory.db`).
- `ADMIN_USER` / `ADMIN_PASSWORD` — credenciais **semente** do usuário admin.

## Requisitos funcionais

### 1. CLI (console script `inv-etl`, via `pyproject.toml`)
Deve ser executável por `uvx --from . inv-etl ...` **e** `uv run inv-etl ...`:

- `inv-etl import` — lê o CSV de `DATASET_PATH`; **upsert** de produtos por `(Company, Model)`; para
  **cada linha** cria uma movimentação **OUT** (`qty=1`, `unit_price=Price`, `region=Dealer_Region`,
  `source="import"`). O histórico de import **não impõe saldo**. Deve ser **idempotente** (rodar 2x
  não duplica movimentações).
- `inv-etl serve --host H --port P` — sobe a **API REST + Web** (FastAPI/uvicorn).
  - **IMPORTANTE:** `serve` é um servidor de longa duração; não o rode em foreground/bloqueante de forma
    a travar a sessão. A avaliação automatizada sobe e encerra o servidor por conta própria.

### 2. Autenticação
- Semeie um usuário **admin** a partir de `ADMIN_USER`/`ADMIN_PASSWORD`, com a senha armazenada em **HASH**
  (use `hashlib`/pbkdf2 ou `passlib` — **NUNCA** texto plano).
- `POST /auth/login` com corpo `{username, password}` → **200** `{token}` (válido) / **401** (inválido).
- **Rotas de escrita** exigem o header `Authorization: Bearer <token>` (sem token → **401/403**).

### 3. API REST (FastAPI)
- `GET /api/products` → lista de produtos: `id, company, model, stock, unit_cost`. (leitura **pública**)
- `POST /api/products` `{company, model, unit_cost}` → cria/retorna o produto. (**PROTEGIDA**)
- `POST /api/movements` `{product_id, type:"in"|"out", qty, unit_price?}` → registra a movimentação;
  `type=in` **soma** ao `stock`, `type=out` **subtrai**. Saída **maior que o stock atual** retorna
  **400** (o estoque **nunca** fica negativo). (**PROTEGIDA**)
- `GET /api/dashboard` → objeto:
  ```json
  {
    "revenue": 0, "cost": 0, "profit": 0,
    "units_sold": 0, "movements": 0,
    "by_company": {"Ford": 0}, "by_region": {"São Paulo": 0}
  }
  ```
  - `revenue` = soma dos `unit_price` das **saídas**.
  - `cost` = soma de `floor(0.8 * price)` das saídas importadas + custos das entradas.
  - `units_sold` = nº de **saídas**; `movements` = nº **total** de movimentações.
  - `by_company` / `by_region` = receita agregada por `Company` / `Dealer_Region`.

### 4. Web
- `GET /` → página **HTML** com um **formulário de login** (campos `username` e `password`, `method="post"`).

## Requisitos não-funcionais / entregáveis obrigatórios
1. `pyproject.toml` — projeto **uv** com console script `inv-etl`.
2. Módulos coesos: ETL/ingestão, autenticação, lógica de estoque, persistência, API/Web, CLI.
3. **Testes (pytest)** cobrindo import, auth (hash/login), estoque (in/out + saldo) e dashboard. Devem **passar**.
4. **README** com instruções de carga (import) e uso (API/Web/dashboard).
5. Config de **lint** (`ruff`, `line-length = 100`) e um workflow de **CI** (GitHub Actions) rodando lint + testes.

> **Não use Docker.** O empacotamento e a execução são via **uv/uvx**. Não crie `Dockerfile` nem `docker-compose.yml`.

### Execução em um único comando (uv/uvx) — obrigatório
- `uv run inv-etl import && uv run inv-etl serve`
- `uvx --from . inv-etl serve`

### Tratamento de erros (obrigatório)
- `DATASET_PATH` ausente/inexistente → mensagem de erro **acionável**, sem stack trace cru (rc ≠ 0).
- Payloads inválidos (ex.: `type` desconhecido, `qty` ≤ 0) → resposta tratada.
- Saída maior que o saldo → **400** (estoque nunca negativo).

## Restrições
- Use apenas bibliotecas reais e existentes do ecossistema Python. **Não invente APIs nem pacotes.**
- Não dependa de serviços externos online.
- Código organizado em camadas/módulos coesos.
