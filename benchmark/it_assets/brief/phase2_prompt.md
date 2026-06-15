# Fase 2 — Refatorar o dashboard em uma aplicação

**Mudança de direção.** Agora **refatore** o dashboard que você acabou de construir, transformando-o numa
**aplicação completa de gestão de movimentação de ativos de TI**. Reaproveite o que fizer sentido do código
existente e reorganize em camadas — não recomece do zero sem necessidade.

## Stack obrigatório (novo)
- **Python 3.12** + **uv**.
- **FastAPI** (API + páginas) + **Jinja2** (templates HTML) + **SQLite** (persistência).
- **Autenticação JWT** e **RBAC** (papéis, ex.: `admin` e `viewer`/`operator`).

## Requisitos
- Migrar a base para **SQLite** (carga a partir de `DATASET_PATH`) com CRUD e **movimentações** de ativos
  (alocação/devolução/transferência) **persistidas**.
- **Telas Jinja2** (ex.: login, listagem/visão de ativos, dashboard de métricas) **e** API REST equivalente.
- **JWT:** `POST /auth/login` com `{username, password}` → `{token}`; rotas protegidas exigem
  `Authorization: Bearer <token>` (sem token → 401).
- **RBAC:** ao menos **dois papéis**; uma ação de escrita/admin **negada com 403** para papel sem permissão.
- **Execução por UM único comando `uvx`** carregando o **`.env` versionado com valores** (inclua `JWT_SECRET`
  e credenciais semente dos usuários/papéis). Console script no `pyproject.toml`; comando no README.
- **Testes unitários (pytest)** cobrindo login JWT, RBAC (papel negado → 403), persistência e carga da base,
  **com medição de cobertura (coverage)** configurada e reportada. (O nível de cobertura é decisão sua.) **Lint** limpo.

## Servidor não-bloqueante
FastAPI/uvicorn é de longa duração — não bloqueie a sessão (a avaliação sobe e encerra por conta própria).
