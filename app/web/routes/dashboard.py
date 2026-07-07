from fastapi import APIRouter, Request
from app.web.dependencies import get_brandos_service
from app.web.templates_env import templates

router = APIRouter()
service = get_brandos_service()

@router.get("/")
async def get_dashboard(request: Request):
    metrics = service.get_dashboard_metrics()
    operating_loop = service.get_today_operating_loop()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "metrics": metrics,
        "operating_loop": operating_loop,
    })
