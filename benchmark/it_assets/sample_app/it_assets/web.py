"""FastAPI: API REST + páginas Jinja2 + JWT + RBAC."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from it_assets import auth as auth_mod
from it_assets.db import connect
from it_assets.ingest import ensure_loaded
from it_assets.metrics import dashboard_metrics, list_assets

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        ensure_loaded()
        yield

    app = FastAPI(title="IT Assets", lifespan=lifespan)

    def get_con():
        con = connect()
        try:
            yield con
        finally:
            con.close()

    def current_user(authorization: str | None = Header(default=None)) -> dict:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="token ausente")
        token = authorization.split(" ", 1)[1].strip()
        claims = auth_mod.decode_token(token)
        if claims is None:
            raise HTTPException(status_code=401, detail="token inválido")
        return {"username": claims.get("sub"), "role": claims.get("role")}

    def require_admin(user: dict = Depends(current_user)) -> dict:
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="acesso negado (requer admin)")
        return user

    # ---- Web (Jinja2) ----
    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return TEMPLATES.TemplateResponse(request, "login.html")

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard_page(request: Request, con=Depends(get_con)):
        return TEMPLATES.TemplateResponse(
            request,
            "dashboard.html",
            {"metrics": dashboard_metrics(con), "assets": list_assets(con)},
        )

    # ---- Auth ----
    @app.post("/auth/login")
    def login(payload: dict, con=Depends(get_con)):
        user = auth_mod.authenticate(
            con, payload.get("username", ""), payload.get("password", "")
        )
        if user is None:
            raise HTTPException(status_code=401, detail="credenciais inválidas")
        token = auth_mod.make_token(user["username"], user["role"])
        return {"token": token, "role": user["role"]}

    # ---- API (leitura pública) ----
    @app.get("/api/assets")
    def api_assets(con=Depends(get_con)):
        return list_assets(con)

    @app.get("/api/dashboard")
    def api_dashboard(con=Depends(get_con)):
        return dashboard_metrics(con)

    # ---- API protegida (escrita) ----
    @app.post("/api/movements")
    def api_create_movement(
        payload: dict, con=Depends(get_con), user: dict = Depends(require_admin)
    ):
        asset_tag = (payload.get("asset_tag") or "").strip()
        action = (payload.get("action") or "").strip().lower()
        if not asset_tag or action not in {"allocate", "return", "transfer", "maintenance"}:
            raise HTTPException(status_code=400, detail="payload inválido")
        cur = con.execute(
            """INSERT INTO movements (asset_tag, asset_type, action, employee,
                   from_location, to_location, status, value)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                asset_tag,
                payload.get("asset_type"),
                action,
                payload.get("employee"),
                payload.get("from_location"),
                payload.get("to_location"),
                payload.get("status"),
                payload.get("value"),
            ),
        )
        con.commit()
        return JSONResponse(status_code=201, content={"id": cur.lastrowid, "asset_tag": asset_tag})

    return app


app = create_app()
