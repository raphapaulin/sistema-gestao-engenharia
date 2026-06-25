from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.config import SESSION_COOKIE_NAME
from backend.config import STATIC_DIR
from backend.database import SessionLocal, init_db
from backend.routes import (
    auth,
    atividades,
    clientes,
    colaboradores,
    cronograma,
    dashboard,
    disponibilidade,
    ordens,
    pagamentos,
    performance,
    servicos,
)
from backend.services.auth_service import get_user_by_id, read_session_token


init_db()


app = FastAPI(
    title="Sistema de Gestao de Engenharia",
    description="Versao demo para gestao de servicos e ordens de engenharia.",
    version="0.1.0",
)


PUBLIC_PATH_PREFIXES = (
    "/static/",
)
PUBLIC_EXACT_PATHS = {"/login", "/favicon.ico"}


def is_public_path(path: str) -> bool:
    return path in PUBLIC_EXACT_PATHS or path.startswith(PUBLIC_PATH_PREFIXES)


def add_no_cache_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.middleware("http")
async def require_login(request: Request, call_next):
    path = request.url.path
    if is_public_path(path):
        return await call_next(request)

    token = request.cookies.get(SESSION_COOKIE_NAME)
    payload = read_session_token(token)
    user = None
    if payload:
        try:
            user_id = int(payload["sub"])
        except (KeyError, TypeError, ValueError):
            user_id = 0

        if user_id:
            with SessionLocal() as db:
                user = get_user_by_id(db, user_id)

    if not user:
        next_url = quote(str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""))
        response = RedirectResponse(url=f"/login?next={next_url}", status_code=303)
        response.delete_cookie(SESSION_COOKIE_NAME, path="/")
        return add_no_cache_headers(response)

    request.state.user = user
    response = await call_next(request)
    return add_no_cache_headers(response)


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(clientes.router)
app.include_router(colaboradores.router)
app.include_router(servicos.router)
app.include_router(ordens.router)
app.include_router(pagamentos.router)
app.include_router(atividades.router)
app.include_router(cronograma.router)
app.include_router(disponibilidade.router)
app.include_router(performance.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    favicon_path = STATIC_DIR / "img" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return Response(status_code=204)


@app.get("/health", tags=["Sistema"])
def health_check():
    return {"status": "ok"}
