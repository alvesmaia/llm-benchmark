# IT Assets — Gestão de Movimentação de Ativos de TI

App de referência do harness: **FastAPI + SQLite + Jinja2 + JWT + RBAC**, executável por um único
comando `uvx`, carregando o `.env` versionado automaticamente.

## Executar (um único comando)

```bash
uvx --from . it-assets serve --host 127.0.0.1 --port 8000
# ou
uv run it-assets serve
```

O servidor carrega a base (CSV em `data/`) no SQLite no boot e semeia os usuários a partir do `.env`.
Para carregar/recarregar manualmente:

```bash
uv run it-assets import
```

## Configuração (`.env` versionado)

O `.env` (com valores de demo) é carregado automaticamente: `JWT_SECRET`, `ADMIN_USER`/`ADMIN_PASSWORD`
(papel `admin`, escrita) e `VIEWER_USER`/`VIEWER_PASSWORD` (papel `viewer`, somente leitura).

## API

- `POST /auth/login` `{username, password}` → `{token, role}` (200) / 401 (inválido).
- `GET /api/dashboard` — métricas de movimentação (público).
- `GET /api/assets` — visão por ativo (público).
- `POST /api/movements` — registra movimentação (**protegida**: Bearer token + papel `admin` → 403 p/ viewer).
- `GET /` — página de login (Jinja2); `GET /dashboard` — dashboard HTML.

## Testes e lint

```bash
uv run pytest        # roda com cobertura (--cov configurado no pyproject)
uv run ruff check .
```

## Robustez (ingestão)

A ingestão é tolerante a dados sujos (campos nulos, ações fora do domínio, valores negativos, datas em
formato alternativo, ids duplicados) — valores inválidos são saneados sem derrubar a carga.
