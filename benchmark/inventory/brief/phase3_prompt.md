# Fase 3 — Versionamento (Git/GitHub)

O repositório já está inicializado e com `origin` + branch configurados pelo harness. Agora versione seu
trabalho de forma profissional:

1. Garanta um `.gitignore` adequado (não comite `.venv/`, banco gerado `*.db`, caches, segredos).
2. Faça **commits significativos** e bem descritos. Prefira **Conventional Commits**
   (`feat:`, `fix:`, `test:`, `docs:`, `chore:`...). Se fizer sentido, separe em mais de um commit lógico
   (ex.: ingestão/ETL, auth, API/dashboard, testes, infra) em vez de um único commit gigante.
3. Crie uma **tag semver** apontando para o estado final, no formato `vX.Y.Z` (ex.: `v0.1.0`).
4. Faça **push** do branch e da(s) tag(s) para o `origin`:
   ```
   git push origin HEAD
   git push origin --tags
   ```
   Se o push falhar por configuração de ambiente, registre o erro mas garanta que commits e tag existem localmente.

Ao final, mostre `git log --oneline` e `git tag`.
