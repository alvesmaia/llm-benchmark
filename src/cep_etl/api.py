"""API REST e interface web com FastAPI."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .query import CepNotFound, query_cep, query_ceps, result_to_dict

app = FastAPI(
    title="CEP ETL API",
    description="Consulta de CEP a partir da base eDNE dos Correios.",
    version="1.0.0",
)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class CepsRequest(BaseModel):
    ceps: list[str]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Página principal com formulário de consulta de CEP."""
    return templates.TemplateResponse(
        request, "index.html", {"results": None, "query": "", "error": None}
    )


@app.post("/", response_class=HTMLResponse)
async def search(request: Request):
    """Processa formulário de consulta de CEP."""
    form = await request.form()
    raw = str(form.get("ceps", ""))
    cep_list = [c.strip() for c in raw.replace(",", "\n").splitlines() if c.strip()]

    if not cep_list:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"results": None, "query": raw, "error": "Informe pelo menos um CEP."},
        )

    results = query_ceps(cep_list)
    results_dicts = [result_to_dict(r) for r in results]
    return templates.TemplateResponse(
        request,
        "index.html",
        {"results": results_dicts, "query": raw, "error": None},
    )


@app.get("/cep/{cep}")
async def get_cep(cep: str):
    """Consulta um CEP específico."""
    result = query_cep(cep)
    if isinstance(result, CepNotFound):
        raise HTTPException(status_code=404, detail=result.erro)
    return result_to_dict(result)


@app.post("/ceps")
async def get_ceps(body: CepsRequest):
    """Consulta múltiplos CEPs em lote."""
    if not body.ceps:
        raise HTTPException(status_code=422, detail="A lista de CEPs não pode ser vazia.")
    results = query_ceps(body.ceps)
    return [result_to_dict(r) for r in results]
