from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import json
import markdown

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

class GenerateCmoRecommendationRequest(BaseModel):
    confirm: bool = False
    window_days: int = 30
    notes: str = None

@router.post("/cmo/recommendation/generate")
async def generate_cmo_recommendation(request: Request, payload: GenerateCmoRecommendationRequest):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmação obrigatória.")
        
    service = request.app.state.brandos_service
    result = service.generate_cmo_recommendation_with_memory(
        confirm=payload.confirm,
        window_days=payload.window_days,
        notes=payload.notes
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
        
    return result

@router.get("/cmo/recommendations", response_class=HTMLResponse)
async def list_cmo_recommendations(request: Request):
    service = request.app.state.brandos_service
    index_path = os.path.join(service.base_dir, "data", "generated", "cmo-recommendations", "index.json")
    
    recommendations = []
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                recommendations = data.get("recommendations", [])
                recommendations.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
        except Exception:
            pass
            
    return templates.TemplateResponse("cmo_recommendation_list.html", {
        "request": request,
        "recommendations": recommendations,
        "active_menu": "/cmo/recommendations"
    })

@router.get("/cmo/recommendations/{recommendation_id}", response_class=HTMLResponse)
async def view_cmo_recommendation(request: Request, recommendation_id: str):
    service = request.app.state.brandos_service
    index_path = os.path.join(service.base_dir, "data", "generated", "cmo-recommendations", "index.json")
    
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Nenhuma recomendação encontrada.")
        
    target = None
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for rec in data.get("recommendations", []):
                if rec.get("id") == recommendation_id:
                    target = rec
                    break
    except Exception:
        pass
        
    if not target:
        raise HTTPException(status_code=404, detail="Recomendação não encontrada.")
        
    file_rel = target.get("file")
    if not file_rel:
        raise HTTPException(status_code=404, detail="Arquivo da recomendação não especificado.")
        
    file_path = os.path.join(service.base_dir, file_rel.replace("/", os.sep))
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo físico da recomendação não encontrado.")
        
    with open(file_path, "r", encoding="utf-8") as f:
        md_content = f.read()
        
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
        
    service = request.app.state.brandos_service
    result = service.create_briefing_from_cmo_recommendation(
        recommendation_id=recommendation_id,
        confirm=payload.confirm,
        notes=payload.notes
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
        
    return JSONResponse(content=result)
