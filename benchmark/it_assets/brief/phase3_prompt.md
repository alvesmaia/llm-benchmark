# Fase 3 — A base mudou: rode os testes e corrija

A base de dados do projeto (em `data/`) **foi alterada**: alguns valores mudaram e podem violar suposições do
seu código (ex.: campos vazios/nulos, ações/categorias fora do domínio, valores negativos, datas em formato
inesperado, ids duplicados). **A base não foi recriada — apenas alguns valores mudaram.**

Sua tarefa:
1. **Rode os testes novamente** (`pytest` com cobertura) e observe as falhas.
2. **Investigue e corrija** os erros na aplicação (ingestão/validação/consultas/telas) para lidar de forma
   **robusta** com os novos dados — sem quebrar o que já funcionava.
3. Garanta que a aplicação **volta a subir** pelo comando único `uvx` e que os **testes passam** novamente.

Ao final, descreva em poucas linhas o que quebrou, a causa e como corrigiu.
