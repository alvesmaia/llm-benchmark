# Desafio: ETL da base de CEP dos Correios (Python)

Você é um engenheiro de software sênior. Implemente, **sozinho e do zero**, uma aplicação Python completa,
pronta para produção, que faz o **ETL da base de CEP dos Correios** e permite **consultar um ou mais CEPs**.
Não peça confirmação: tome as decisões necessárias e entregue o projeto inteiro.

## Contexto da base de dados (eDNE Básico)

A base oficial é o **eDNE Básico** dos Correios, distribuída como arquivos texto delimitados.

- **Encoding:** Latin-1 / Windows-1252 (NÃO é UTF-8).
- **Separador de campos:** arroba `@`.
- **Sem cabeçalho** nas linhas de dados.
- O caminho da base é fornecido na variável de ambiente **`DNE_PATH`** (uma pasta contendo os arquivos abaixo).

Arquivos relevantes (subset que você deve processar):

### `LOG_LOCALIDADE.TXT`
Campos, em ordem, separados por `@`:
`LOC_NU` `@` `UFE_SG` `@` `LOC_NO` `@` `CEP` `@` `LOC_IN_SIT` `@` `LOC_IN_TIPO_LOC` `@` `LOC_NU_SUB` `@` `LOC_NO_ABREV` `@` `MUN_NU`

- `LOC_NU`: id da localidade. `UFE_SG`: UF. `LOC_NO`: nome da localidade (município).
- `CEP`: **CEP único** da localidade (pode estar vazio para localidades com faixa por logradouro).

### `LOG_BAIRRO.TXT`
`BAI_NU` `@` `UFE_SG` `@` `LOC_NU` `@` `BAI_NO` `@` `BAI_NO_ABREV`

- `BAI_NU`: id do bairro. `LOC_NU`: FK para a localidade. `BAI_NO`: nome do bairro.

### `LOG_LOGRADOURO_<UF>.TXT` (um arquivo por UF, ex.: `LOG_LOGRADOURO_SP.TXT`)
`LOG_NU` `@` `UFE_SG` `@` `LOC_NU` `@` `BAI_NU_INI` `@` `BAI_NU_FIM` `@` `LOG_NO` `@` `LOG_COMPLEMENTO` `@` `CEP` `@` `TLO_TX` `@` `LOG_STA_TLO` `@` `LOG_NO_ABREV`

- `LOG_NU`: id do logradouro. `LOC_NU`: FK localidade. `BAI_NU_INI`: FK bairro inicial.
- `LOG_NO`: nome do logradouro. `CEP`: CEP do logradouro. `TLO_TX`: tipo (Rua, Avenida, etc.).

## Requisitos funcionais

### 1. ETL
- Ler todos os arquivos `LOG_LOCALIDADE.TXT`, `LOG_BAIRRO.TXT` e `LOG_LOGRADOURO_*.TXT` de `DNE_PATH`.
- Respeitar encoding Latin-1 e separador `@`.
- Normalizar e **carregar em banco de dados** (SQLite por padrão — caminho via `DB_PATH`, default `cep.db`;
  suportar Postgres via `DATABASE_URL` é um diferencial, opcional).
- A carga deve ser **idempotente**: rodar o ETL duas vezes não duplica dados nem quebra.
- O schema deve ter **índice por CEP** (consulta por CEP é a operação central).

### 2. Consulta por CEP (um ou mais)
Dado um CEP (com ou sem hífen/máscara, ex.: `01001-000` ou `01001000`), retornar o endereço completo:
`cep`, `logradouro`, `tipo_logradouro`, `bairro`, `localidade` (município), `uf`.

- Deve aceitar **vários CEPs de uma vez**.
- **Fallback:** se não houver logradouro específico para o CEP, retornar o CEP de **localidade** (município/UF)
  correspondente, quando existir.
- CEP **não encontrado** deve ser reportado claramente (não pode quebrar a consulta dos demais CEPs do lote).

### 3. Três interfaces (todas obrigatórias)
- **CLI** (console script `cep-etl`):
  - `cep-etl load` — roda o ETL (lê `DNE_PATH`, popula o banco).
  - `cep-etl query <cep> [<cep> ...]` — consulta 1+ CEPs; suportar `--json` para saída JSON.
  - `cep-etl serve` — sobe a Web + API.
- **API REST** (FastAPI):
  - `GET /cep/{cep}` — consulta um CEP.
  - `POST /ceps` — corpo `{"ceps": ["01001000", "20040002"]}`, consulta em lote.
  - Respostas JSON; 404 para CEP não encontrado no `GET`.
- **Web**: página com **formulário** que aceita um ou mais CEPs (ex.: separados por vírgula/quebra de linha)
  e exibe os resultados em **tabela**.

## Requisitos não-funcionais / entregáveis obrigatórios

1. `pyproject.toml` — **projeto uv** com console script `cep-etl`.
2. Módulo de ETL (parsing + carga).
3. Módulo de consulta (lógica de busca + fallback).
4. CLI (`cep-etl`).
5. App FastAPI (API + Web).
6. Templates da interface Web.
7. **Testes (pytest)** cobrindo ETL, consulta, fallback e casos de erro. Devem **passar**.
8. **README** com instruções de carga e uso das três interfaces.
9. Config de **lint** (`ruff`) e um workflow de **CI** (GitHub Actions) rodando lint + testes.

> **Não use Docker.** O empacotamento e a execução são via **uv/uvx** (ver abaixo). Não crie
> `Dockerfile` nem `docker-compose.yml`.

### Execução em um único comando (uv/uvx) — obrigatório
O projeto deve rodar standalone:
- `uv run cep-etl load && uv run cep-etl serve`
- `uvx --from . cep-etl serve`

### Tratamento de erros (obrigatório)
- CEP com formato inválido (não numérico / tamanho errado) → erro claro, sem stack trace cru.
- CEP não encontrado → resposta tratada.
- `DNE_PATH` ausente ou arquivos faltando → mensagem de erro acionável.

## Restrições
- Use apenas bibliotecas reais e existentes do ecossistema Python. **Não invente APIs nem pacotes.**
- Não dependa de serviços externos online para a consulta (a consulta é contra o banco carregado pelo ETL).
- Código organizado em camadas/módulos coesos.

## Variáveis de ambiente fornecidas pelo harness
- `DNE_PATH` — pasta com os arquivos `LOG_*.TXT`.
- `DB_PATH` — caminho do SQLite (default `cep.db`).
- (Git) o repositório já está inicializado com `origin` e branch configurados; nas instruções de versionamento
  você só precisará de `git add/commit/tag/push`.
