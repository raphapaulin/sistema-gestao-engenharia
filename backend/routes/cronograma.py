from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.config import TEMPLATES_DIR
from backend.database import get_db
from backend.services.atividades_service import (
    STATUS_OPTIONS,
    list_clientes_options,
    list_colaboradores_options,
)
from backend.services.cronograma_service import list_calendar_events


router = APIRouter(prefix="/cronograma", tags=["Cronograma"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
def cronograma_index(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        name="cronograma/index.html",
        request=request,
        context={
            "request": request,
            "active_page": "cronograma",
            "status_options": STATUS_OPTIONS,
            "colaboradores": list_colaboradores_options(db),
            "clientes": list_clientes_options(db),
        },
    )


@router.get("/eventos")
def cronograma_events(
    start: str = "",
    end: str = "",
    id_colaborador: str = "",
    id_cliente: str = "",
    status: str = "",
    db: Session = Depends(get_db),
):
    return list_calendar_events(
        db,
        start=start,
        end=end,
        id_colaborador=id_colaborador,
        id_cliente=id_cliente,
        status=status,
    )
