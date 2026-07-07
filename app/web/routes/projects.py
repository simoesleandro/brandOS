from fastapi import APIRouter, Request
from app.web.dependencies import get_brandos_service
from app.web.templates_env import templates

router = APIRouter(prefix="/projects", tags=["projects"])
service = get_brandos_service()

@router.get("/")
async def get_projects(request: Request):
    projects = service.get_projects_list()
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "projects": projects
    })
