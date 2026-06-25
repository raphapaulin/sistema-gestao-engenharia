from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.config import TEMPLATES_DIR
from backend.database import get_db
from backend.services.ordens_service import (
    STATUS_OPTIONS,
    OrdemForm,
    create_ordem,
    delete_ordem,
    get_ordem,
    list_clientes_options,
    list_colaboradores_options,
    list_ordens,
    list_servicos_options,
    normalize_ordem_form,
    today_iso,
    update_ordem,
    update_ordem_status,
    validate_ordem_form,
)


router = APIRouter(prefix="/ordens", tags=["Ordens de Serviço"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _redirect_to_list(message_type: str, message: str) -> RedirectResponse:
    query = urlencode({message_type: message})
    return RedirectResponse(url=f"/ordens?{query}", status_code=303)


def _form_context(
    db: Session,
    request: Request,
    form_title: str,
    form_action: str,
    ordem,
    errors: list[str] | None = None,
) -> dict:
    return {
        "request": request,
        "active_page": "ordens",
        "form_title": form_title,
        "form_action": form_action,
        "ordem": ordem,
        "errors": errors or [],
        "status_options": STATUS_OPTIONS,
        "clientes": list_clientes_options(db),
        "colaboradores": list_colaboradores_options(db),
        "servicos": list_servicos_options(db),
    }


@router.get("", response_class=HTMLResponse)
def ordens_index(
    request: Request,
    q: str = "",
    success: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    ordens = list_ordens(db, q)
    return templates.TemplateResponse(
        name="ordens/list.html",
        request=request,
        context={
            "request": request,
            "active_page": "ordens",
            "ordens": ordens,
            "q": q,
            "success": success,
            "error": error,
            "status_options": STATUS_OPTIONS,
        },
    )


@router.get("/nova", response_class=HTMLResponse)
def ordens_new(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        name="ordens/form.html",
        request=request,
        context=_form_context(
            db=db,
            request=request,
            form_title="Nova Ordem de Serviço",
            form_action="/ordens/nova",
            ordem=OrdemForm(data_abertura=today_iso()),
        ),
    )


@router.post("/nova", response_class=HTMLResponse)
def ordens_create(
    request: Request,
    data_abertura: str = Form(""),
    id_cliente: str = Form(""),
    id_colaborador: str = Form(""),
    id_servico: str = Form(""),
    status: str = Form(""),
    db: Session = Depends(get_db),
):
    form = normalize_ordem_form(
        data_abertura,
        id_cliente,
        id_colaborador,
        id_servico,
        status,
    )
    errors, data = validate_ordem_form(db, form)

    if errors:
        return templates.TemplateResponse(
            name="ordens/form.html",
            request=request,
            context=_form_context(
                db=db,
                request=request,
                form_title="Nova Ordem de Serviço",
                form_action="/ordens/nova",
                ordem=form,
                errors=errors,
            ),
            status_code=400,
        )

    try:
        create_ordem(db, data)
    except ValueError as exc:
        return templates.TemplateResponse(
            name="ordens/form.html",
            request=request,
            context=_form_context(
                db=db,
                request=request,
                form_title="Nova Ordem de Serviço",
                form_action="/ordens/nova",
                ordem=form,
                errors=[str(exc)],
            ),
            status_code=400,
        )

    return _redirect_to_list("success", "Ordem de serviço cadastrada com sucesso.")


@router.get("/{ordem_id}/editar", response_class=HTMLResponse)
def ordens_edit(request: Request, ordem_id: int, db: Session = Depends(get_db)):
    ordem = get_ordem(db, ordem_id)
    if not ordem:
        return _redirect_to_list("error", "Ordem de serviço não encontrada.")

    return templates.TemplateResponse(
        name="ordens/form.html",
        request=request,
        context=_form_context(
            db=db,
            request=request,
            form_title="Editar Ordem de Serviço",
            form_action=f"/ordens/{ordem_id}/editar",
            ordem=ordem,
        ),
    )


@router.post("/{ordem_id}/editar", response_class=HTMLResponse)
def ordens_update(
    request: Request,
    ordem_id: int,
    data_abertura: str = Form(""),
    id_cliente: str = Form(""),
    id_colaborador: str = Form(""),
    id_servico: str = Form(""),
    status: str = Form(""),
    db: Session = Depends(get_db),
):
    if not get_ordem(db, ordem_id):
        return _redirect_to_list("error", "Ordem de serviço não encontrada.")

    form = normalize_ordem_form(
        data_abertura,
        id_cliente,
        id_colaborador,
        id_servico,
        status,
    )
    errors, data = validate_ordem_form(db, form)

    if errors:
        return templates.TemplateResponse(
            name="ordens/form.html",
            request=request,
            context=_form_context(
                db=db,
                request=request,
                form_title="Editar Ordem de Serviço",
                form_action=f"/ordens/{ordem_id}/editar",
                ordem=form,
                errors=errors,
            ),
            status_code=400,
        )

    try:
        update_ordem(db, ordem_id, data)
    except ValueError as exc:
        return templates.TemplateResponse(
            name="ordens/form.html",
            request=request,
            context=_form_context(
                db=db,
                request=request,
                form_title="Editar Ordem de Serviço",
                form_action=f"/ordens/{ordem_id}/editar",
                ordem=form,
                errors=[str(exc)],
            ),
            status_code=400,
        )

    return _redirect_to_list("success", "Ordem de serviço atualizada com sucesso.")


@router.post("/{ordem_id}/status")
def ordens_status_update(
    ordem_id: int,
    status: str = Form(""),
    db: Session = Depends(get_db),
):
    if not get_ordem(db, ordem_id):
        return _redirect_to_list("error", "Ordem de serviço não encontrada.")

    try:
        update_ordem_status(db, ordem_id, status)
    except ValueError as exc:
        return _redirect_to_list("error", str(exc))

    return _redirect_to_list("success", "Status da ordem atualizado com sucesso.")


@router.post("/{ordem_id}/excluir")
def ordens_delete(ordem_id: int, db: Session = Depends(get_db)):
    if not get_ordem(db, ordem_id):
        return _redirect_to_list("error", "Ordem de serviço não encontrada.")

    try:
        delete_ordem(db, ordem_id)
    except ValueError as exc:
        return _redirect_to_list("error", str(exc))

    return _redirect_to_list("success", "Ordem de serviço excluída com sucesso.")
