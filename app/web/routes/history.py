from fastapi import APIRouter, Request
from app.core.brandos_service import BrandOSService
from app.web.templates_env import templates

router = APIRouter(prefix="/history", tags=["history"])
service = BrandOSService()

@router.get("/")
async def get_history(request: Request):
    history = service.list_history()
    return templates.TemplateResponse("history.html", {
        "request": request,
        "history": history
    })
