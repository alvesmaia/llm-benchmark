"""API REST (FastAPI) + interface Web de consulta de CEP."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from cep_etl.query import CepInvalidoError, lookup, lookup_many

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

app = FastAPI(title="CEP ETL", version="0.1.0")


class CepsBatch(BaseModel):
    ceps: list[str]


@app.get("/cep/{cep}")
def get_cep(cep: str):
    try:
        found = lookup(cep)
    except CepInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if found is None:
        raise HTTPException(status_code=404, detail="CEP não encontrado")
    return found


@app.post("/ceps")
def post_ceps(batch: CepsBatch):
    return lookup_many(batch.ceps)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, ceps: str | None = None):
    results = []
    if ceps:
        items = [c.strip() for c in ceps.replace("\n", ",").split(",") if c.strip()]
        results = lookup_many(items)
    return TEMPLATES.TemplateResponse(
        request, "index.html", {"results": results, "ceps": ceps or ""}
    )
