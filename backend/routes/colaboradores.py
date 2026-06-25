from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.config import TEMPLATES_DIR
from backend.database import get_db
from backend.services.colaboradores_service import (
    CARGO_OPTIONS,
    TIPO_VINCULO_OPTIONS,
    ColaboradorForm,
    create_colaborador,
    delete_colaborador,
    get_colaborador,
    list_colaboradores,
    normalize_colaborador_form,
    update_colaborador,
    validate_colaborador_form,
)


router = APIRouter(prefix="/colaboradores", tags=["Colaboradores"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _redirect_to_list(message_type: str, message: str) -> RedirectResponse:
    query = urlencode({message_type: message})
    return RedirectResponse(url=f"/colaboradores?{query}", status_code=303)


def _form_context(
    request: Request,
    form_title: str,
    form_action: str,
    colaborador,
    errors: list[str] | None = None,
) -> dict:
    return {
        "request": request,
        "active_page": "colaboradores",
        "form_title": form_title,
        "form_action": form_action,
        "colaborador": colaborador,
        "errors": errors or [],
        "cargo_options": CARGO_OPTIONS,
        "tipo_vinculo_options": TIPO_VINCULO_OPTIONS,
    }


@router.get("", response_class=HTMLResponse)
def colaboradores_index(
    request: Request,
    q: str = "",
    success: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    colaboradores = list_colaboradores(db, q)
    return templates.TemplateResponse(
        name="colaboradores/list.html",
        request=request,
        context={
            "request": request,
            "active_page": "colaboradores",
            "colaboradores": colaboradores,
            "q": q,
            "success": success,
            "error": error,
        },
    )


@router.get("/novo", response_class=HTMLResponse)
def colaboradores_new(request: Request):
    return templates.TemplateResponse(
        name="colaboradores/form.html",
        request=request,
        context=_form_context(
            request=request,
            form_title="Novo Colaborador",
            form_action="/colaboradores/novo",
            colaborador=ColaboradorForm(),
        ),
    )


@router.post("/novo", response_class=HTMLResponse)
def colaboradores_create(
    request: Request,
    nome: str = Form(""),
    cargo: str = Form(""),
    email: str = Form(""),
    telefone: str = Form(""),
    tipo_vinculo: str = Form(""),
    registro_profissional: str = Form(""),
    db: Session = Depends(get_db),
):
    form = normalize_colaborador_form(
        nome,
        cargo,
        email,
        telefone,
        tipo_vinculo,
        registro_profissional,
    )
    errors = validate_colaborador_form(db, form)

    if errors:
        return templates.TemplateResponse(
            name="colaboradores/form.html",
            request=request,
            context=_form_context(
                request=request,
                form_title="Novo Colaborador",
                form_action="/colaboradores/novo",
                colaborador=form,
                errors=errors,
            ),
            status_code=400,
        )

    try:
        create_colaborador(db, form)
    except ValueError as exc:
        return templates.TemplateResponse(
            name="colaboradores/form.html",
            request=request,
            context=_form_context(
                request=request,
                form_title="Novo Colaborador",
                form_action="/colaboradores/novo",
                colaborador=form,
                errors=[str(exc)],
            ),
            status_code=400,
        )

    return _redirect_to_list("success", "Colaborador cadastrado com sucesso.")


@router.get("/{colaborador_id}/editar", response_class=HTMLResponse)
def colaboradores_edit(
    request: Request,
    colaborador_id: int,
    db: Session = Depends(get_db),
):
    colaborador = get_colaborador(db, colaborador_id)
    if not colaborador:
        return _redirect_to_list("error", "Colaborador não encontrado.")

    return templates.TemplateResponse(
        name="colaboradores/form.html",
        request=request,
        context=_form_context(
            request=request,
            form_title="Editar Colaborador",
            form_action=f"/colaboradores/{colaborador_id}/editar",
            colaborador=colaborador,
        ),
    )


@router.post("/{colaborador_id}/editar", response_class=HTMLResponse)
def colaboradores_update(
    request: Request,
    colaborador_id: int,
    nome: str = Form(""),
    cargo: str = Form(""),
    email: str = Form(""),
    telefone: str = Form(""),
    tipo_vinculo: str = Form(""),
    registro_profissional: str = Form(""),
    db: Session = Depends(get_db),
):
    if not get_colaborador(db, colaborador_id):
        return _redirect_to_list("error", "Colaborador não encontrado.")

    form = normalize_colaborador_form(
        nome,
        cargo,
        email,
        telefone,
        tipo_vinculo,
        registro_profissional,
    )
    errors = validate_colaborador_form(db, form, colaborador_id)

    if errors:
        return templates.TemplateResponse(
            name="colaboradores/form.html",
            request=request,
            context=_form_context(
                request=request,
                form_title="Editar Colaborador",
                form_action=f"/colaboradores/{colaborador_id}/editar",
                colaborador=form,
                errors=errors,
            ),
            status_code=400,
        )

    try:
        update_colaborador(db, colaborador_id, form)
    except ValueError as exc:
        return templates.TemplateResponse(
            name="colaboradores/form.html",
            request=request,
            context=_form_context(
                request=request,
                form_title="Editar Colaborador",
                form_action=f"/colaboradores/{colaborador_id}/editar",
                colaborador=form,
                errors=[str(exc)],
            ),
            status_code=400,
        )

    return _redirect_to_list("success", "Colaborador atualizado com sucesso.")


@router.post("/{colaborador_id}/excluir")
def colaboradores_delete(colaborador_id: int, db: Session = Depends(get_db)):
    if not get_colaborador(db, colaborador_id):
        return _redirect_to_list("error", "Colaborador não encontrado.")

    delete_colaborador(db, colaborador_id)
    return _redirect_to_list("success", "Colaborador excluído com sucesso.")
