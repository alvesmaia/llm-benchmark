"""API REST (FastAPI) + interface Web. Camada de transporte HTTP."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from inv_etl import auth, inventory
from inv_etl.db import connect, init_schema

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _bootstrap() -> None:
    con = connect()
    init_schema(con)
    auth.seed_admin(con)
    con.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):  # pragma: no cover - exercido pelos checks de boot
    _bootstrap()
    yield


app = FastAPI(title="Inventory ETL", version="0.1.0", lifespan=lifespan)


def require_user(authorization: str | None = Header(default=None)) -> str:
    """Dependência de autorização: exige header Authorization: Bearer <token>."""
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    user = auth.user_for_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="não autenticado")
    return user


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class LoginIn(BaseModel):
    username: str
    password: str


class ProductIn(BaseModel):
    company: str
    model: str
    unit_cost: int = 0


class MovementIn(BaseModel):
    product_id: int
    type: str
    qty: int
    unit_price: int | None = None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.post("/auth/login")
def auth_login(body: LoginIn):
    con = connect()
    init_schema(con)
    auth.seed_admin(con)
    token = auth.login(con, body.username, body.password)
    con.close()
    if token is None:
        raise HTTPException(status_code=401, detail="credenciais inválidas")
    return {"token": token}


# ---------------------------------------------------------------------------
# Produtos
# ---------------------------------------------------------------------------
@app.get("/api/products")
def get_products():
    con = connect()
    init_schema(con)
    out = inventory.list_products(con)
    con.close()
    return out


@app.post("/api/products", status_code=201)
def create_product(body: ProductIn, _user: str = Depends(require_user)):
    con = connect()
    init_schema(con)
    pid = inventory.upsert_product(con, body.company, body.model, unit_cost=body.unit_cost)
    con.commit()
    prod = inventory.get_product(con, pid)
    con.close()
    return prod


# ---------------------------------------------------------------------------
# Movimentações
# ---------------------------------------------------------------------------
@app.post("/api/movements", status_code=201)
def create_movement(body: MovementIn, _user: str = Depends(require_user)):
    con = connect()
    init_schema(con)
    try:
        result = inventory.register_movement(
            con, body.product_id, body.type, body.qty,
            unit_price=body.unit_price or 0,
        )
    except inventory.StockError as e:
        con.close()
        raise HTTPException(status_code=400, detail=str(e)) from e
    con.close()
    return result


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.get("/api/dashboard")
def get_dashboard():
    con = connect()
    init_schema(con)
    out = inventory.dashboard(con)
    con.close()
    return out


# ---------------------------------------------------------------------------
# Web (login)
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return TEMPLATES.TemplateResponse(request, "index.html", {})


@app.post("/", response_class=HTMLResponse)
def index_login(request: Request, username: str = Form(...), password: str = Form(...)):
    con = connect()
    init_schema(con)
    auth.seed_admin(con)
    token = auth.login(con, username, password)
    con.close()
    ctx = {"token": token, "error": None if token else "Credenciais inválidas",
           "username": username}
    return TEMPLATES.TemplateResponse(request, "index.html", ctx)
