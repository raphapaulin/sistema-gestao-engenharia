from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.config import TEMPLATES_DIR
from backend.database import get_db
from backend.services.servicos_service import (
    ServicoForm,
    create_servico,
    delete_servico,
    get_servico,
    list_servicos,
    normalize_servico_form,
    update_servico,
    validate_servico_form,
)


router = APIRouter(prefix="/servicos", tags=["Serviços"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _redirect_to_list(message_type: str, message: str) -> RedirectResponse:
    query = urlencode({message_type: message})
    return RedirectResponse(url=f"/servicos?{query}", status_code=303)


def _form_context(
    request: Request,
    form_title: str,
    form_action: str,
    servico,
    errors: list[str] | None = None,
) -> dict:
    return {
        "request": request,
        "active_page": "servicos",
        "form_title": form_title,
        "form_action": form_action,
        "servico": servico,
        "errors": errors or [],
    }


@router.get("", response_class=HTMLResponse)
def servicos_index(
    request: Request,
    q: str = "",
    success: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    servicos = list_servicos(db, q)
    return templates.TemplateResponse(
        name="servicos/list.html",
        request=request,
        context={
            "request": request,
            "active_page": "servicos",
            "servicos": servicos,
            "q": q,
            "success": success,
            "error": error,
        },
    )


@router.get("/novo", response_class=HTMLResponse)
def servicos_new(request: Request):
    return templates.TemplateResponse(
        name="servicos/form.html",
        request=request,
        context=_form_context(
            request=request,
            form_title="Novo Serviço",
            form_action="/servicos/novo",
            servico=ServicoForm(),
        ),
    )


@router.post("/novo", response_class=HTMLResponse)
def servicos_create(
    request: Request,
    nome: str = Form(""),
    descricao: str = Form(""),
    preco_base: str = Form(""),
    db: Session = Depends(get_db),
):
    form = normalize_servico_form(nome, descricao, preco_base)
    errors, parsed_preco_base = validate_servico_form(form)

    if errors:
        return templates.TemplateResponse(
            name="servicos/form.html",
            request=request,
            context=_form_context(
                request=request,
                form_title="Novo Serviço",
                form_action="/servicos/novo",
                servico=form,
                errors=errors,
            ),
            status_code=400,
        )

    try:
        create_servico(db, form, parsed_preco_base)
    except ValueError as exc:
        return templates.TemplateResponse(
            name="servicos/form.html",
            request=request,
            context=_form_context(
                request=request,
                form_title="Novo Serviço",
                form_action="/servicos/novo",
                servico=form,
                errors=[str(exc)],
            ),
            status_code=400,
        )

    return _redirect_to_list("success", "Serviço cadastrado com sucesso.")


@router.get("/{servico_id}/editar", response_class=HTMLResponse)
def servicos_edit(request: Request, servico_id: int, db: Session = Depends(get_db)):
    servico = get_servico(db, servico_id)
    if not servico:
        return _redirect_to_list("error", "Serviço não encontrado.")

    return templates.TemplateResponse(
        name="servicos/form.html",
        request=request,
        context=_form_context(
            request=request,
            form_title="Editar Serviço",
            form_action=f"/servicos/{servico_id}/editar",
            servico=servico,
        ),
    )


@router.post("/{servico_id}/editar", response_class=HTMLResponse)
def servicos_update(
    request: Request,
    servico_id: int,
    nome: str = Form(""),
    descricao: str = Form(""),
    preco_base: str = Form(""),
    db: Session = Depends(get_db),
):
    if not get_servico(db, servico_id):
        return _redirect_to_list("error", "Serviço não encontrado.")

    form = normalize_servico_form(nome, descricao, preco_base)
    errors, parsed_preco_base = validate_servico_form(form)

    if errors:
        return templates.TemplateResponse(
            name="servicos/form.html",
            request=request,
            context=_form_context(
                request=request,
                form_title="Editar Serviço",
                form_action=f"/servicos/{servico_id}/editar",
                servico=form,
                errors=errors,
            ),
            status_code=400,
        )

    try:
        update_servico(db, servico_id, form, parsed_preco_base)
    except ValueError as exc:
        return templates.TemplateResponse(
            name="servicos/form.html",
            request=request,
            context=_form_context(
                request=request,
                form_title="Editar Serviço",
                form_action=f"/servicos/{servico_id}/editar",
                servico=form,
                errors=[str(exc)],
            ),
            status_code=400,
        )

    return _redirect_to_list("success", "Serviço atualizado com sucesso.")


@router.post("/{servico_id}/excluir")
def servicos_delete(servico_id: int, db: Session = Depends(get_db)):
    if not get_servico(db, servico_id):
        return _redirect_to_list("error", "Serviço não encontrado.")

    try:
        delete_servico(db, servico_id)
    except ValueError as exc:
        return _redirect_to_list("error", str(exc))

    return _redirect_to_list("success", "Serviço excluído com sucesso.")
