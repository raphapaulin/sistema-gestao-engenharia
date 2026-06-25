from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.config import SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS, TEMPLATES_DIR
from backend.database import SessionLocal, get_db
from backend.services.auth_service import (
    authenticate_user,
    create_session_token,
    get_user_by_id,
    read_session_token,
)


router = APIRouter(tags=["Autenticação"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _safe_next_url(next_url: str) -> str:
    if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
        return "/"
    return next_url


def _add_no_cache_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _current_user_from_cookie(request: Request) -> dict | None:
    payload = read_session_token(request.cookies.get(SESSION_COOKIE_NAME))
    if not payload:
        return None

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None

    with SessionLocal() as db:
        return get_user_by_id(db, user_id)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = ""):
    if _current_user_from_cookie(request):
        response = RedirectResponse(url=_safe_next_url(next), status_code=303)
        return _add_no_cache_headers(response)

    response = templates.TemplateResponse(
        name="auth/login.html",
        request=request,
        context={
            "request": request,
            "next_url": _safe_next_url(next),
            "error": "",
        },
    )
    return _add_no_cache_headers(response)


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(""),
    senha: str = Form(""),
    next_url: str = Form("/"),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, email, senha)
    if not user:
        response = templates.TemplateResponse(
            name="auth/login.html",
            request=request,
            context={
                "request": request,
                "next_url": _safe_next_url(next_url),
                "error": "E-mail ou senha inválidos. Confira os dados e tente novamente.",
            },
            status_code=400,
        )
        return _add_no_cache_headers(response)

    response = RedirectResponse(url=_safe_next_url(next_url), status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(user),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return _add_no_cache_headers(response)


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return _add_no_cache_headers(response)
