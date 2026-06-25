from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.config import TEMPLATES_DIR
from backend.database import get_db
from backend.services.clientes_service import (
    ClientForm,
    create_client,
    delete_client,
    get_client,
    list_clients,
    normalize_client_form,
    update_client,
    validate_client_form,
)


router = APIRouter(prefix="/clientes", tags=["Clientes"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _redirect_to_list(message_type: str, message: str) -> RedirectResponse:
    query = urlencode({message_type: message})
    return RedirectResponse(url=f"/clientes?{query}", status_code=303)


@router.get("", response_class=HTMLResponse)
def clients_index(
    request: Request,
    q: str = "",
    success: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    clients = list_clients(db, q)
    return templates.TemplateResponse(
        name="clientes/list.html",
        request=request,
        context={
            "request": request,
            "active_page": "clientes",
            "clients": clients,
            "q": q,
            "success": success,
            "error": error,
        },
    )


@router.get("/novo", response_class=HTMLResponse)
def clients_new(request: Request):
    return templates.TemplateResponse(
        name="clientes/form.html",
        request=request,
        context={
            "request": request,
            "active_page": "clientes",
            "form_title": "Novo Cliente",
            "form_action": "/clientes/novo",
            "client": ClientForm(),
            "errors": [],
        },
    )


@router.post("/novo", response_class=HTMLResponse)
def clients_create(
    request: Request,
    nome: str = Form(""),
    empresa: str = Form(""),
    telefone: str = Form(""),
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    form = normalize_client_form(nome, empresa, telefone, email)
    errors = validate_client_form(db, form)

    if errors:
        return templates.TemplateResponse(
            name="clientes/form.html",
            request=request,
            context={
                "request": request,
                "active_page": "clientes",
                "form_title": "Novo Cliente",
                "form_action": "/clientes/novo",
                "client": form,
                "errors": errors,
            },
            status_code=400,
        )

    try:
        create_client(db, form)
    except ValueError as exc:
        return templates.TemplateResponse(
            name="clientes/form.html",
            request=request,
            context={
                "request": request,
                "active_page": "clientes",
                "form_title": "Novo Cliente",
                "form_action": "/clientes/novo",
                "client": form,
                "errors": [str(exc)],
            },
            status_code=400,
        )

    return _redirect_to_list("success", "Cliente cadastrado com sucesso.")


@router.get("/{client_id}/editar", response_class=HTMLResponse)
def clients_edit(request: Request, client_id: int, db: Session = Depends(get_db)):
    client = get_client(db, client_id)
    if not client:
        return _redirect_to_list("error", "Cliente não encontrado.")

    return templates.TemplateResponse(
        name="clientes/form.html",
        request=request,
        context={
            "request": request,
            "active_page": "clientes",
            "form_title": "Editar Cliente",
            "form_action": f"/clientes/{client_id}/editar",
            "client": client,
            "errors": [],
        },
    )


@router.post("/{client_id}/editar", response_class=HTMLResponse)
def clients_update(
    request: Request,
    client_id: int,
    nome: str = Form(""),
    empresa: str = Form(""),
    telefone: str = Form(""),
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    if not get_client(db, client_id):
        return _redirect_to_list("error", "Cliente não encontrado.")

    form = normalize_client_form(nome, empresa, telefone, email)
    errors = validate_client_form(db, form, client_id)

    if errors:
        return templates.TemplateResponse(
            name="clientes/form.html",
            request=request,
            context={
                "request": request,
                "active_page": "clientes",
                "form_title": "Editar Cliente",
                "form_action": f"/clientes/{client_id}/editar",
                "client": form,
                "errors": errors,
            },
            status_code=400,
        )

    try:
        update_client(db, client_id, form)
    except ValueError as exc:
        return templates.TemplateResponse(
            name="clientes/form.html",
            request=request,
            context={
                "request": request,
                "active_page": "clientes",
                "form_title": "Editar Cliente",
                "form_action": f"/clientes/{client_id}/editar",
                "client": form,
                "errors": [str(exc)],
            },
            status_code=400,
        )

    return _redirect_to_list("success", "Cliente atualizado com sucesso.")


@router.post("/{client_id}/excluir")
def clients_delete(client_id: int, db: Session = Depends(get_db)):
    if not get_client(db, client_id):
        return _redirect_to_list("error", "Cliente não encontrado.")

    try:
        delete_client(db, client_id)
    except ValueError as exc:
        return _redirect_to_list("error", str(exc))

    return _redirect_to_list("success", "Cliente excluído com sucesso.")
