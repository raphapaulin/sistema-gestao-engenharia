from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.config import TEMPLATES_DIR
from backend.database import get_db
from backend.services.dashboard_service import get_dashboard_data


router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    dashboard_data = get_dashboard_data(db)
    return templates.TemplateResponse(
        name="dashboard.html",
        request=request,
        context={
            "request": request,
            "active_page": "dashboard",
            **dashboard_data,
        },
    )
