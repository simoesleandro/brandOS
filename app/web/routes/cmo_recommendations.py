from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import markdown
from app.web.dependencies import get_brandos_service

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
service = get_brandos_service()

class GenerateCmoRecommendationRequest(BaseModel):
    confirm: bool = False
    window_days: int = 30
    notes: str = None

@router.post("/cmo/recommendation/generate")
async def generate_cmo_recommendation(request: Request, payload: GenerateCmoRecommendationRequest):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmação obrigatória.")
        
    result = service.generate_cmo_recommendation_with_memory(
        confirm=payload.confirm,
        window_days=payload.window_days,
        notes=payload.notes
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
        
    return result

class ArchiveCmoRequest(BaseModel):
    confirm: bool = False

@router.post("/cmo/recommendations/{recommendation_id}/archive")
async def archive_cmo_recommendation(request: Request, recommendation_id: str, payload: ArchiveCmoRequest):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmação obrigatória.")
        
    result = service.archive_cmo_recommendation(recommendation_id, confirm=payload.confirm)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
        
    return JSONResponse(content=result)

@router.post("/cmo/recommendations/archive-stale")
async def archive_stale_cmo_recommendations(request: Request, payload: ArchiveCmoRequest):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmação obrigatória.")

    result = service.cmo_service.archive_stale_recommendations(confirm=payload.confirm)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return JSONResponse(content=result)

@router.get("/cmo/recommendations", response_class=HTMLResponse)
async def list_cmo_recommendations(request: Request):
    inbox = service.cmo_service.list_recommendation_inbox()
            
    return templates.TemplateResponse("cmo_recommendation_list.html", {
        "request": request,
        "active_recommendation": inbox["active_recommendation"],
        "recommendations": inbox["active_recommendations"],
        "recommendation_history": inbox["recommendation_history"],
        "archived_recommendations": inbox["archived_recommendations"],
        "duplicate_count": inbox["duplicate_count"],
        "total_count": inbox["total_count"],
        "visible_count": inbox["visible_count"],
        "error_msg": inbox["error_msg"],
        "active_menu": "/cmo/recommendations"
    })

@router.get("/cmo/recommendations/{recommendation_id}", response_class=HTMLResponse)
async def view_cmo_recommendation(request: Request, recommendation_id: str):
    target, md_content = service.cmo_service.read_recommendation_markdown(recommendation_id)

    if not target:
        raise HTTPException(status_code=404, detail="Recomendação não encontrada.")

    if not target.get("file"):
        raise HTTPException(status_code=404, detail="Arquivo da recomendação não especificado.")

    if md_content is None:
        raise HTTPException(status_code=404, detail="Arquivo físico da recomendação não encontrado.")

    html_content = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])
    target["html_content"] = html_content
    
    return templates.TemplateResponse("cmo_recommendation_detail.html", {
        "request": request,
        "recommendation": target,
        "active_menu": "/cmo/recommendations"
    })


class CreateBriefingRequest(BaseModel):
    confirm: bool = False
    notes: str = None

@router.post("/cmo/recommendations/{recommendation_id}/create-briefing")
async def create_briefing_from_cmo(request: Request, recommendation_id: str, payload: CreateBriefingRequest):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmação obrigatória.")
        
    result = service.create_briefing_from_cmo_recommendation(
        recommendation_id=recommendation_id,
        confirm=payload.confirm,
        notes=payload.notes
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
        
    return JSONResponse(content=result)
