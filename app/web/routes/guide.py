from fastapi import APIRouter, Request

from app.web.templates_env import templates


router = APIRouter(prefix="/guide", tags=["guide"])


@router.get("/")
async def get_guide(request: Request):
    return templates.TemplateResponse("guide.html", {
        "request": request,
        "active_menu": "/guide",
    })
