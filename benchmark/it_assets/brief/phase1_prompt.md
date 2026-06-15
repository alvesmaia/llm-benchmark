# Fase 1 — Planejar e implementar o dashboard

Você é um engenheiro de software sênior. Planeje e implemente, do zero e de forma autônoma, um **dashboard em
Python com Streamlit** para **gestão de movimentação de ativos de TI**, a partir da base fornecida. Não peça
confirmação: tome as decisões de modelagem e entregue funcionando.

## Base de dados (fornecida)
O caminho do CSV está na env `DATASET_PATH`. Contém o histórico de **movimentações de ativos de TI** (ex.:
alocação, devolução, transferência e manutenção de dispositivos ligados a colaboradores e locais). **Copie
esse CSV para uma pasta `data/` na raiz do projeto** e passe a usá-lo de lá — o app deve ser **autossuficiente**
(rodar sem depender de caminho externo). Explore as colunas e **modele como achar melhor — a estrutura final
é sua decisão.**

## Stack obrigatório
- **Python 3.12** gerenciado por **uv** (`pyproject.toml`; sem pip/conda; **sem Docker**).
- **Streamlit** para o dashboard.

## Requisitos
- Ler a base e apresentar métricas úteis de movimentação (ex.: ativos por status/local/colaborador,
  movimentações no tempo, disponibilidade/ciclo de vida — o recorte é sua decisão).
- **Execução por UM único comando `uvx`** a partir da raiz, **carregando automaticamente** a configuração de
  um **`.env` versionado com valores reais** (use `python-dotenv` ou equivalente; commite o `.env`, não só um
  `.env.example`). Declare um console script no `pyproject.toml` e **documente o comando exato no README**.
- **Testes unitários (pytest)** da lógica do dashboard, **com medição de cobertura (coverage)** — configure e
  reporte a cobertura da suíte. (Decida você o nível adequado de cobertura.)
- `README` (como rodar) e **lint (ruff, line-length 100)**.

## Servidor não-bloqueante
Streamlit é servidor de longa duração — **não** o deixe em foreground travando a sessão. A avaliação sobe e
encerra o app por conta própria; se for testar, suba em segundo plano/timeout e encerre.
