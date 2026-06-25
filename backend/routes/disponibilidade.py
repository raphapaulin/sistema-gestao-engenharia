from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.config import TEMPLATES_DIR
from backend.database import get_db
from backend.services.atividades_service import (
    STATUS_OPTIONS,
    list_colaboradores_options,
)
from backend.services.disponibilidade_service import (
    get_availability_analysis,
    get_hours_report,
)


router = APIRouter(tags=["Disponibilidade"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/disponibilidade", response_class=HTMLResponse)
def disponibilidade_index(
    request: Request,
    id_colaborador: str = "",
    data: str = "",
    duracao_minutos: str = "60",
    db: Session = Depends(get_db),
):
    analysis = get_availability_analysis(
        db,
        id_colaborador=id_colaborador,
        data=data or date.today().isoformat(),
        duracao_minutos=duracao_minutos,
    )
    return templates.TemplateResponse(
        name="disponibilidade/index.html",
        request=request,
        context={
            "request": request,
            "active_page": "disponibilidade",
            "colaboradores": list_colaboradores_options(db),
            "id_colaborador": id_colaborador,
            "data": analysis["data"],
            "duracao_minutos": analysis["duracao_minutos"],
            "analysis": analysis,
        },
    )


@router.get("/relatorio-horas", response_class=HTMLResponse)
def relatorio_horas_index(
    request: Request,
    id_colaborador: str = "",
    data_inicio: str = "",
    data_fim: str = "",
    status: str = "",
    db: Session = Depends(get_db),
):
    report = get_hours_report(
        db,
        id_colaborador=id_colaborador,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=status,
    )
    return templates.TemplateResponse(
        name="disponibilidade/relatorio_horas.html",
        request=request,
        context={
            "request": request,
            "active_page": "relatorio_horas",
            "colaboradores": list_colaboradores_options(db),
            "status_options": STATUS_OPTIONS,
            "id_colaborador": id_colaborador,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "status_filter": status,
            "report": report,
        },
    )
