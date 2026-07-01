from fastapi import APIRouter, Request
from app.core.brandos_service import BrandOSService
from app.web.templates_env import templates

router = APIRouter(prefix="/projects", tags=["projects"])
service = BrandOSService()

@router.get("/")
async def get_projects(request: Request):
    projects = service.get_projects_list()
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "projects": projects
    })
