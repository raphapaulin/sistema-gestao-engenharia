from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.config import TEMPLATES_DIR
from backend.database import get_db
from backend.services.atividades_service import (
    STATUS_OPTIONS,
    AtividadeForm,
    create_atividade,
    delete_atividade,
    get_atividade,
    list_atividades,
    list_clientes_options,
    list_colaboradores_options,
    list_ordens_options,
    list_servicos_options,
    normalize_atividade_form,
    today_iso,
    update_atividade,
    update_atividade_status,
    validate_atividade_form,
)


router = APIRouter(prefix="/atividades", tags=["Atividades"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _redirect_to_list(message_type: str, message: str) -> RedirectResponse:
    query = urlencode({message_type: message})
    return RedirectResponse(url=f"/atividades?{query}", status_code=303)


def _form_context(
    db: Session,
    request: Request,
    form_title: str,
    form_action: str,
    atividade,
    errors: list[str] | None = None,
) -> dict:
    return {
        "request": request,
        "active_page": "atividades",
        "form_title": form_title,
        "form_action": form_action,
        "atividade": atividade,
        "errors": errors or [],
        "status_options": STATUS_OPTIONS,
        "colaboradores": list_colaboradores_options(db),
        "clientes": list_clientes_options(db),
        "servicos": list_servicos_options(db),
        "ordens": list_ordens_options(db),
    }


@router.get("", response_class=HTMLResponse)
def atividades_index(
    request: Request,
    id_colaborador: str = "",
    id_cliente: str = "",
    id_servico: str = "",
    status: str = "",
    data_inicio: str = "",
    data_fim: str = "",
    success: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    atividades = list_atividades(
        db,
        id_colaborador=id_colaborador,
        id_cliente=id_cliente,
        id_servico=id_servico,
        status=status,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    return templates.TemplateResponse(
        name="atividades/list.html",
        request=request,
        context={
            "request": request,
            "active_page": "atividades",
            "atividades": atividades,
            "id_colaborador": id_colaborador,
            "id_cliente": id_cliente,
            "id_servico": id_servico,
            "status_filter": status,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "success": success,
            "error": error,
            "status_options": STATUS_OPTIONS,
            "colaboradores": list_colaboradores_options(db),
            "clientes": list_clientes_options(db),
            "servicos": list_servicos_options(db),
        },
    )


@router.get("/nova", response_class=HTMLResponse)
def atividades_new(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        name="atividades/form.html",
        request=request,
        context=_form_context(
            db=db,
            request=request,
            form_title="Nova Atividade",
            form_action="/atividades/nova",
            atividade=AtividadeForm(data_atividade=today_iso()),
        ),
    )


@router.post("/nova", response_class=HTMLResponse)
def atividades_create(
    request: Request,
    titulo: str = Form(""),
    descricao: str = Form(""),
    data_atividade: str = Form(""),
    hora_inicio: str = Form(""),
    hora_fim: str = Form(""),
    status: str = Form(""),
    id_colaborador: str = Form(""),
    id_cliente: str = Form(""),
    id_servico: str = Form(""),
    id_ordem: str = Form(""),
    observacoes: str = Form(""),
    db: Session = Depends(get_db),
):
    form = normalize_atividade_form(
        titulo,
        descricao,
        data_atividade,
        hora_inicio,
        hora_fim,
        status,
        id_colaborador,
        id_cliente,
        id_servico,
        id_ordem,
        observacoes,
    )
    errors, data = validate_atividade_form(db, form)

    if errors:
        return templates.TemplateResponse(
            name="atividades/form.html",
            request=request,
            context=_form_context(
                db=db,
                request=request,
                form_title="Nova Atividade",
                form_action="/atividades/nova",
                atividade=form,
                errors=errors,
            ),
            status_code=400,
        )

    try:
        create_atividade(db, data)
    except ValueError as exc:
        return templates.TemplateResponse(
            name="atividades/form.html",
            request=request,
            context=_form_context(
                db=db,
                request=request,
                form_title="Nova Atividade",
                form_action="/atividades/nova",
                atividade=form,
                errors=[str(exc)],
            ),
            status_code=400,
        )

    return _redirect_to_list("success", "Atividade cadastrada com sucesso.")


@router.get("/{atividade_id}/editar", response_class=HTMLResponse)
def atividades_edit(
    request: Request,
    atividade_id: int,
    db: Session = Depends(get_db),
):
    atividade = get_atividade(db, atividade_id)
    if not atividade:
        return _redirect_to_list("error", "Atividade não encontrada.")

    return templates.TemplateResponse(
        name="atividades/form.html",
        request=request,
        context=_form_context(
            db=db,
            request=request,
            form_title="Editar Atividade",
            form_action=f"/atividades/{atividade_id}/editar",
            atividade=atividade,
        ),
    )


@router.post("/{atividade_id}/editar", response_class=HTMLResponse)
def atividades_update(
    request: Request,
    atividade_id: int,
    titulo: str = Form(""),
    descricao: str = Form(""),
    data_atividade: str = Form(""),
    hora_inicio: str = Form(""),
    hora_fim: str = Form(""),
    status: str = Form(""),
    id_colaborador: str = Form(""),
    id_cliente: str = Form(""),
    id_servico: str = Form(""),
    id_ordem: str = Form(""),
    observacoes: str = Form(""),
    db: Session = Depends(get_db),
):
    if not get_atividade(db, atividade_id):
        return _redirect_to_list("error", "Atividade não encontrada.")

    form = normalize_atividade_form(
        titulo,
        descricao,
        data_atividade,
        hora_inicio,
        hora_fim,
        status,
        id_colaborador,
        id_cliente,
        id_servico,
        id_ordem,
        observacoes,
    )
    errors, data = validate_atividade_form(db, form)

    if errors:
        return templates.TemplateResponse(
            name="atividades/form.html",
            request=request,
            context=_form_context(
                db=db,
                request=request,
                form_title="Editar Atividade",
                form_action=f"/atividades/{atividade_id}/editar",
                atividade=form,
                errors=errors,
            ),
            status_code=400,
        )

    try:
        update_atividade(db, atividade_id, data)
    except ValueError as exc:
        return templates.TemplateResponse(
            name="atividades/form.html",
            request=request,
            context=_form_context(
                db=db,
                request=request,
                form_title="Editar Atividade",
                form_action=f"/atividades/{atividade_id}/editar",
                atividade=form,
                errors=[str(exc)],
            ),
            status_code=400,
        )

    return _redirect_to_list("success", "Atividade atualizada com sucesso.")


@router.post("/{atividade_id}/status")
def atividades_status_update(
    atividade_id: int,
    status: str = Form(""),
    db: Session = Depends(get_db),
):
    if not get_atividade(db, atividade_id):
        return _redirect_to_list("error", "Atividade não encontrada.")

    try:
        update_atividade_status(db, atividade_id, status)
    except ValueError as exc:
        return _redirect_to_list("error", str(exc))

    return _redirect_to_list("success", "Status da atividade atualizado com sucesso.")


@router.post("/{atividade_id}/excluir")
def atividades_delete(atividade_id: int, db: Session = Depends(get_db)):
    if not get_atividade(db, atividade_id):
        return _redirect_to_list("error", "Atividade não encontrada.")

    try:
        delete_atividade(db, atividade_id)
    except ValueError as exc:
        return _redirect_to_list("error", str(exc))

    return _redirect_to_list("success", "Atividade excluída com sucesso.")
