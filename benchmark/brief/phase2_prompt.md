# Fase 2 — Validação e correção

Continuando o mesmo projeto que você acabou de construir, agora **valide e corrija** até funcionar de ponta a ponta:

1. Rode o ETL contra `DNE_PATH` e confirme que o banco é populado sem erros (`uv run cep-etl load`).
2. Rode a suíte de testes (`uv run pytest` ou equivalente) e **corrija** até todos passarem.
3. Rode o lint (`uv run ruff check .`) e **corrija todos os erros** reportados até `ruff check` passar limpo.
4. Confirme que a Web e a API sobem. **NÃO rode `cep-etl serve` em foreground/bloqueante** — um servidor
   não retorna e travaria esta sessão. Se quiser testar manualmente, suba em **segundo plano** (ou com
   timeout), faça a consulta de exemplo e **encerre o servidor** logo em seguida. Em geral nem é preciso:
   a avaliação automatizada já valida o boot da Web/API por conta própria.
5. Garanta a execução em um único comando (sem deixar processo preso): `uvx --from . cep-etl --help` e o
   `serve` devem funcionar.

Conserte tudo o que estiver quebrado. Não faça commit ainda — isso é a Fase 3.

Ao final, descreva em poucas linhas o que validou e o que corrigiu.
