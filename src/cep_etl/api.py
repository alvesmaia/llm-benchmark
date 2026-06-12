"""API REST e interface Web com FastAPI."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .query import CepNotFound, query_cep, query_ceps, result_to_dict

TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(
    title="CEP ETL API",
    description="Consulta da base de CEP dos Correios (eDNE Básico)",
    version="0.1.0",
)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class CepsRequest(BaseModel):
    ceps: list[str]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Página Web com formulário de consulta de CEPs."""
    return templates.TemplateResponse(request, "index.html", {"results": None})


@app.post("/", response_class=HTMLResponse)
async def index_post(request: Request):
    """Processa o formulário de consulta de CEPs."""
    import re

    form = await request.form()
    raw = form.get("ceps", "")
    cep_list = [c.strip() for c in re.split(r"[,;\s\n]+", raw) if c.strip()]

    if not cep_list:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"results": None, "error": "Informe pelo menos um CEP."},
        )

    results = query_ceps(cep_list)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"results": [result_to_dict(r) for r in results]},
    )


@app.get("/cep/{cep}")
async def get_cep(cep: str):
    """Consulta um único CEP."""
    result = query_cep(cep)
    if isinstance(result, CepNotFound):
        raise HTTPException(status_code=404, detail=result.error)
    return result_to_dict(result)


@app.post("/ceps")
async def post_ceps(body: CepsRequest):
    """Consulta múltiplos CEPs em lote."""
    results = query_ceps(body.ceps)
    return [result_to_dict(r) for r in results]
