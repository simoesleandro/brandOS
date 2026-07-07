from fastapi import APIRouter, Request, Form, Body
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import os
from pydantic import BaseModel
from typing import Optional
from app.web.dependencies import get_brandos_service
from app.web.templates_env import templates

router = APIRouter(prefix="/strategic-memory", tags=["strategic_memory"])
brandos_service = get_brandos_service()

class GenerateMemoryRequest(BaseModel):
    confirm: bool
    window_days: Optional[int] = 30
    notes: Optional[str] = None

@router.get("", response_class=HTMLResponse)
async def list_strategic_memory(request: Request):
    """Lista o histórico de memórias estratégicas."""
    import json
    
    mem_dir = os.path.join(brandos_service.base_dir, "data", "generated", "strategic-memory")
    index_path = os.path.join(mem_dir, "index.json")
    
    memories = []
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                memories = data.get("memories", [])
                memories.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
        except Exception:
            pass # se corrompido, lida no backend na hora de gerar
            
    return templates.TemplateResponse(
        "strategic_memory_list.html",
        {"request": request, "memories": memories, "active_tab": "strategic_memory"}
    )

@router.get("/{memory_id}", response_class=HTMLResponse)
async def view_strategic_memory(request: Request, memory_id: str):
    """Exibe os detalhes de uma memória estratégica específica."""
    import json
    import markdown
    
    mem_dir = os.path.join(brandos_service.base_dir, "data", "generated", "strategic-memory")
    index_path = os.path.join(mem_dir, "index.json")
    
    memory_meta = None
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for m in data.get("memories", []):
                    if m.get("id") == memory_id:
                        memory_meta = m
                        break
        except Exception:
            pass
            
    if not memory_meta:
        return templates.TemplateResponse(
            "strategic_memory_detail.html",
            {
                "request": request,
                "error": "Memória não encontrada.",
                "active_tab": "strategic_memory"
            }
        )
        
    file_path = memory_meta.get("file")
    html_content = ""
    raw_content = ""
    
    if file_path:
        abs_path = os.path.join(brandos_service.base_dir, file_path.replace("/", os.sep))
        if os.path.exists(abs_path):
            with open(abs_path, "r", encoding="utf-8") as f:
                raw_content = f.read()
                html_content = markdown.markdown(raw_content)
        else:
            raw_content = "Arquivo não encontrado."
            
    return templates.TemplateResponse(
        "strategic_memory_detail.html",
        {
            "request": request,
            "memory": memory_meta,
            "content_html": html_content,
            "content_raw": raw_content,
            "active_tab": "strategic_memory"
        }
    )

@router.post("/generate")
async def generate_memory(payload: GenerateMemoryRequest = Body(...)):
    """Gera uma nova memória estratégica para o CMO Agent."""
    
    if not payload.confirm:
        return JSONResponse(status_code=400, content={"detail": "Confirmação necessária."})
        
    result = brandos_service.generate_strategic_memory(
        confirm=payload.confirm,
        window_days=payload.window_days,
        notes=payload.notes
    )
    
    if result.get("status") == "success":
        return {"success": True, **result}
    else:
        return JSONResponse(status_code=400, content={"detail": result.get("message", "Erro desconhecido.")})
