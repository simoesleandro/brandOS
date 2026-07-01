from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from app.core.brandos_service import BrandOSService
from app.web.templates_env import templates

router = APIRouter(prefix="/generate", tags=["generations"])
service = BrandOSService()

@router.get("/")
async def get_generate_page(request: Request):
    projects = service.get_projects_list()
    return templates.TemplateResponse("generations.html", {
        "request": request,
        "projects": projects
    })

@router.post("/weekly")
async def generate_weekly_auto(request: Request):
    # Modo automático
    try:
        service.run_weekly_generation(mode="auto")
        return RedirectResponse(url="/publications", status_code=303)
    except Exception as e:
        return {"error": str(e)}

@router.post("/briefing")
async def generate_weekly_briefing(request: Request, project: str = Form(""), briefing: str = Form("")):
    # Modo direcionado
    try:
        service.run_weekly_generation(mode="manual", project=project, briefing=briefing)
        return RedirectResponse(url="/publications", status_code=303)
    except Exception as e:
        return {"error": str(e)}
