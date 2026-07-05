from fastapi import APIRouter, Request
from app.core.brandos_service import BrandOSService
from app.web.templates_env import templates

router = APIRouter(tags=["ops"])
service = BrandOSService()

@router.get("/ops")
async def ops_dashboard(request: Request):
    data = service.get_ops_dashboard()
    
    return templates.TemplateResponse("ops_dashboard.html", {
        "request": request,
        "counts": data.get("counts", {}),
        "pipeline_groups": data.get("pipeline_groups", {}),
        "post_publish_groups": data.get("post_publish_groups", {}),
        "lists": data.get("lists", {}),
        "error": data.get("error")
    })
