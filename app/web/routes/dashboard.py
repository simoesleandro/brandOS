from fastapi import APIRouter, Request
from app.core.brandos_service import BrandOSService
from app.web.templates_env import templates

router = APIRouter()
service = BrandOSService()

@router.get("/")
async def get_dashboard(request: Request):
    metrics = service.get_dashboard_metrics()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "metrics": metrics
    })
