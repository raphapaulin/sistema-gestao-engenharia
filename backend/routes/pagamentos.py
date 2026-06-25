from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.config import TEMPLATES_DIR
from backend.database import get_db
from backend.services.pagamentos_service import (
    STATUS_OPTIONS,
    PagamentoForm,
    create_pagamento,
    delete_pagamento,
    get_pagamento,
    list_ordens_options,
    list_pagamentos,
    normalize_pagamento_form,
    update_pagamento,
    update_pagamento_status,
    validate_pagamento_form,
)


router = APIRouter(prefix="/pagamentos", tags=["Pagamentos"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _redirect_to_list(message_type: str, message: str) -> RedirectResponse:
    query = urlencode({message_type: message})
    return RedirectResponse(url=f"/pagamentos?{query}", status_code=303)


def _form_context(
    db: Session,
    request: Request,
    form_title: str,
    form_action: str,
    pagamento,
    current_ordem_id: int | None = None,
    errors: list[str] | None = None,
) -> dict:
    return {
        "request": request,
        "active_page": "pagamentos",
        "form_title": form_title,
        "form_action": form_action,
        "pagamento": pagamento,
        "errors": errors or [],
        "status_options": STATUS_OPTIONS,
        "ordens": list_ordens_options(db, current_ordem_id),
    }


@router.get("", response_class=HTMLResponse)
def pagamentos_index(
    request: Request,
    q: str = "",
    status: str = "",
    data_inicio: str = "",
    data_fim: str = "",
    success: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    pagamentos = list_pagamentos(db, q, status, data_inicio, data_fim)
    return templates.TemplateResponse(
        name="pagamentos/list.html",
        request=request,
        context={
            "request": request,
            "active_page": "pagamentos",
            "pagamentos": pagamentos,
            "q": q,
            "status_filter": status,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "success": success,
            "error": error,
            "status_options": STATUS_OPTIONS,
        },
    )


@router.get("/novo", response_class=HTMLResponse)
def pagamentos_new(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        name="pagamentos/form.html",
        request=request,
        context=_form_context(
            db=db,
            request=request,
            form_title="Novo Pagamento",
            form_action="/pagamentos/novo",
            pagamento=PagamentoForm(status="pendente"),
        ),
    )


@router.post("/novo", response_class=HTMLResponse)
def pagamentos_create(
    request: Request,
    id_ordem: str = Form(""),
    valor: str = Form(""),
    status: str = Form(""),
    data_pagamento: str = Form(""),
    db: Session = Depends(get_db),
):
    form = normalize_pagamento_form(id_ordem, valor, status, data_pagamento)
    errors, data = validate_pagamento_form(db, form)

    if errors:
        return templates.TemplateResponse(
            name="pagamentos/form.html",
            request=request,
            context=_form_context(
                db=db,
                request=request,
                form_title="Novo Pagamento",
                form_action="/pagamentos/novo",
                pagamento=form,
                current_ordem_id=data.get("id_ordem"),
                errors=errors,
            ),
            status_code=400,
        )

    try:
        create_pagamento(db, data)
    except ValueError as exc:
        return templates.TemplateResponse(
            name="pagamentos/form.html",
            request=request,
            context=_form_context(
                db=db,
                request=request,
                form_title="Novo Pagamento",
                form_action="/pagamentos/novo",
                pagamento=form,
                current_ordem_id=data.get("id_ordem"),
                errors=[str(exc)],
            ),
            status_code=400,
        )

    return _redirect_to_list("success", "Pagamento cadastrado com sucesso.")


@router.get("/{pagamento_id}/editar", response_class=HTMLResponse)
def pagamentos_edit(
    request: Request,
    pagamento_id: int,
    db: Session = Depends(get_db),
):
    pagamento = get_pagamento(db, pagamento_id)
    if not pagamento:
        return _redirect_to_list("error", "Pagamento não encontrado.")

    return templates.TemplateResponse(
        name="pagamentos/form.html",
        request=request,
        context=_form_context(
            db=db,
            request=request,
            form_title="Editar Pagamento",
            form_action=f"/pagamentos/{pagamento_id}/editar",
            pagamento=pagamento,
            current_ordem_id=pagamento["id_ordem"],
        ),
    )


@router.post("/{pagamento_id}/editar", response_class=HTMLResponse)
def pagamentos_update(
    request: Request,
    pagamento_id: int,
    id_ordem: str = Form(""),
    valor: str = Form(""),
    status: str = Form(""),
    data_pagamento: str = Form(""),
    db: Session = Depends(get_db),
):
    if not get_pagamento(db, pagamento_id):
        return _redirect_to_list("error", "Pagamento não encontrado.")

    form = normalize_pagamento_form(id_ordem, valor, status, data_pagamento)
    errors, data = validate_pagamento_form(db, form, pagamento_id)

    if errors:
        return templates.TemplateResponse(
            name="pagamentos/form.html",
            request=request,
            context=_form_context(
                db=db,
                request=request,
                form_title="Editar Pagamento",
                form_action=f"/pagamentos/{pagamento_id}/editar",
                pagamento=form,
                current_ordem_id=data.get("id_ordem"),
                errors=errors,
            ),
            status_code=400,
        )

    try:
        update_pagamento(db, pagamento_id, data)
    except ValueError as exc:
        return templates.TemplateResponse(
            name="pagamentos/form.html",
            request=request,
            context=_form_context(
                db=db,
                request=request,
                form_title="Editar Pagamento",
                form_action=f"/pagamentos/{pagamento_id}/editar",
                pagamento=form,
                current_ordem_id=data.get("id_ordem"),
                errors=[str(exc)],
            ),
            status_code=400,
        )

    return _redirect_to_list("success", "Pagamento atualizado com sucesso.")


@router.post("/{pagamento_id}/status")
def pagamentos_status_update(
    pagamento_id: int,
    status: str = Form(""),
    db: Session = Depends(get_db),
):
    if not get_pagamento(db, pagamento_id):
        return _redirect_to_list("error", "Pagamento não encontrado.")

    try:
        update_pagamento_status(db, pagamento_id, status)
    except ValueError as exc:
        return _redirect_to_list("error", str(exc))

    return _redirect_to_list("success", "Status do pagamento atualizado com sucesso.")


@router.post("/{pagamento_id}/excluir")
def pagamentos_delete(pagamento_id: int, db: Session = Depends(get_db)):
    if not get_pagamento(db, pagamento_id):
        return _redirect_to_list("error", "Pagamento não encontrado.")

    try:
        delete_pagamento(db, pagamento_id)
    except ValueError as exc:
        return _redirect_to_list("error", str(exc))

    return _redirect_to_list("success", "Pagamento excluído com sucesso.")
