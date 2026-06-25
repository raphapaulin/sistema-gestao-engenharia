from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.config import TEMPLATES_DIR
from backend.database import get_db
from backend.services.atividades_service import STATUS_OPTIONS, list_colaboradores_options
from backend.services.performance_service import (
    get_colaborador_performance_detail,
    get_performance_data,
)


router = APIRouter(prefix="/performance", tags=["Performance"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _query_string(params: dict[str, str]) -> str:
    return urlencode({key: value for key, value in params.items() if value})


@router.get("", response_class=HTMLResponse)
def performance_index(
    request: Request,
    id_colaborador: str = "",
    data_inicio: str = "",
    data_fim: str = "",
    status: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    performance = get_performance_data(
        db,
        id_colaborador=id_colaborador,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=status,
    )
    detail_query = _query_string(
        {
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "status": status,
        }
    )

    return templates.TemplateResponse(
        name="performance/index.html",
        request=request,
        context={
            "request": request,
            "active_page": "performance",
            "colaboradores": list_colaboradores_options(db),
            "status_options": STATUS_OPTIONS,
            "id_colaborador": id_colaborador,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "status_filter": status,
            "error": error,
            "detail_query": detail_query,
            "performance": performance,
        },
    )


@router.get("/{colaborador_id}", response_class=HTMLResponse)
def performance_detail(
    request: Request,
    colaborador_id: int,
    data_inicio: str = "",
    data_fim: str = "",
    status: str = "",
    db: Session = Depends(get_db),
):
    detail = get_colaborador_performance_detail(
        db,
        colaborador_id=colaborador_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=status,
    )
    if detail is None:
        query = urlencode({"error": "Colaborador não encontrado."})
        return RedirectResponse(
            url=f"/performance?{query}",
            status_code=303,
        )

    return templates.TemplateResponse(
        name="performance/detail.html",
        request=request,
        context={
            "request": request,
            "active_page": "performance",
            "status_options": STATUS_OPTIONS,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "status_filter": status,
            "detail": detail,
        },
    )
