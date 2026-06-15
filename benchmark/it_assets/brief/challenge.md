# Contrato mínimo — Gestão de Movimentação de Ativos de TI

Este é o **contrato mínimo** que a avaliação automatizada verifica (caixa-preta). A **estrutura interna é
livre** — só os pontos abaixo são exigidos para que as checagens determinísticas funcionem. Tudo o mais
(modelagem, camadas, nomes) é decisão sua.

## Base de dados
- O caminho do CSV é fornecido na env **`DATASET_PATH`** (UTF-8, com cabeçalho). Cada linha é uma
  **movimentação** de um ativo de TI (alocação/devolução/transferência/manutenção).
- A Fase 1 deve **copiar** o CSV para `data/` na raiz do projeto; o app passa a ler de lá (autossuficiente).

## Estado final avaliado (pós-Fase 2 e Fase 3)
A aplicação final é **FastAPI + SQLite + Jinja2 + JWT + RBAC**, executável por **um único comando `uvx`**.

### Console script
- O `pyproject.toml` declara um **console script `it-assets`**, executável por
  `uvx --from . it-assets ...` **e** `uv run it-assets ...`.
- O subcomando de servidor é **`it-assets serve --host H --port P`** (sobe API + Web).
- (Opcional, recomendado) `it-assets import` carrega o SQLite a partir de `DATASET_PATH`. Se o seed/carga
  ocorrer no boot do servidor, o `import` pode ser um no-op idempotente.

### Configuração
- O app **carrega automaticamente** um **`.env` versionado com valores** (use `python-dotenv` ou equivalente).
  O `.env` inclui `JWT_SECRET` e as **credenciais semente** de usuários/papéis.
- Variáveis fornecidas pelo harness: `DATASET_PATH`, `DB_PATH` (caminho do SQLite),
  `ADMIN_USER`/`ADMIN_PASSWORD` (admin), `VIEWER_USER`/`VIEWER_PASSWORD` (papel sem permissão de escrita).

### Autenticação JWT
- `POST /auth/login` com `{username, password}` → **200** `{token}` (válido) / **401** (inválido).
- Pelo menos **uma rota protegida** exige `Authorization: Bearer <token>` (sem token → **401/403**).

### RBAC
- Ao menos **dois papéis** (ex.: `admin` e `viewer`). Uma **ação de escrita/admin** com um usuário de papel
  sem permissão é **negada com 403**.

### Persistência / ingestão
- O **SQLite** (em `DB_PATH`) é **populado a partir de `DATASET_PATH`** (≥1 tabela com linhas de ativos/
  movimentações).

### Web (Jinja2)
- `GET /` (ou rota de login) responde **HTML** com um **formulário de login** (campos `username`/`password`).

## Testes e qualidade
- **Testes pytest** com **cobertura medida** (ex.: `pytest --cov`); os testes devem **passar**.
- **Lint** com `ruff` (`line-length = 100`).
- `README` documentando o comando único `uvx`.

## Restrições
- Apenas bibliotecas reais do ecossistema Python. **Não invente pacotes/APIs.** **Sem Docker.**
- O servidor é de longa duração — **não** bloqueie a sessão; a avaliação sobe/encerra por conta própria.
