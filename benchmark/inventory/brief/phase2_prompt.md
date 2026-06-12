# Fase 2 — Validação e correção

Continuando o mesmo projeto que você acabou de construir, agora **valide e corrija** até funcionar de ponta a ponta:

1. Rode a importação contra `DATASET_PATH` e confirme que o banco é populado sem erros
   (`uv run inv-etl import`): produtos e movimentações devem existir.
2. Rode a suíte de testes (`uv run pytest` ou equivalente) e **corrija** até todos passarem.
3. Rode o lint (`uv run ruff check .`) e **corrija todos os erros** reportados até `ruff check` passar limpo.
4. Confirme que a Web e a API sobem. **NÃO rode `inv-etl serve` em foreground/bloqueante** — um servidor
   não retorna e travaria esta sessão. Se quiser testar manualmente, suba em **segundo plano** (ou com
   timeout), faça as consultas de exemplo (login, `GET /api/dashboard`) e **encerre o servidor** logo em
   seguida. Em geral nem é preciso: a avaliação automatizada já valida o boot da Web/API por conta própria.
5. Garanta a execução em um único comando (sem deixar processo preso): `uvx --from . inv-etl --help` e o
   `serve` devem funcionar.

Verifique especialmente: login válido retorna token e inválido retorna 401; rotas de escrita exigem token;
entrada/saída atualizam o estoque e saída maior que o saldo retorna 400; o dashboard bate com os dados importados.

Conserte tudo o que estiver quebrado. Não faça commit ainda — isso é a Fase 3.

Ao final, descreva em poucas linhas o que validou e o que corrigiu.
