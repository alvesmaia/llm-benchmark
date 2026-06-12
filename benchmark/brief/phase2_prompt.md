# Fase 2 — Validação e correção

Continuando o mesmo projeto que você acabou de construir, agora **valide e corrija** até funcionar de ponta a ponta:

1. Rode o ETL contra `DNE_PATH` e confirme que o banco é populado sem erros (`uv run cep-etl load`).
2. Rode a suíte de testes (`uv run pytest` ou equivalente) e **corrija** até todos passarem.
3. Rode o lint (`uv run ruff check .`) e **corrija todos os erros** reportados até `ruff check` passar limpo.
4. Suba a aplicação localmente (`uv run cep-etl serve`) e confirme que a Web e a API respondem; faça uma
   consulta de exemplo a um CEP presente na base de teste.
5. Garanta a execução em um único comando: `uvx --from . cep-etl serve` deve funcionar.

Conserte tudo o que estiver quebrado. Não faça commit ainda — isso é a Fase 3.

Ao final, descreva em poucas linhas o que validou e o que corrigiu.
