from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.web.dependencies import get_brandos_service
import os

router = APIRouter(prefix="/briefings", tags=["briefings"])

# Diretório base do projeto (na raiz brandos)
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
templates = Jinja2Templates(directory=os.path.join(base_dir, "app", "web", "templates"))

# Instancia o serviço
service = get_brandos_service()

@router.get("", response_class=HTMLResponse)
async def list_briefings(request: Request):
    """
    Lista todos os briefings salvos.
    """
    briefings = service.list_briefings()
    return templates.TemplateResponse(
        "briefings_list.html",
        {"request": request, "briefings": briefings}
    )

@router.get("/{filename}", response_class=HTMLResponse)
async def view_briefing(request: Request, filename: str):
    """
    Exibe os detalhes de um briefing específico.
    """
    try:
        import markdown
        raw_content = service.read_briefing(filename)
        html_content = markdown.markdown(raw_content, extensions=["extra", "nl2br"])
        
        status = "unknown"
        status_match = __import__('re').search(r'^Status:\s*(.*)$', raw_content, __import__('re').MULTILINE | __import__('re').IGNORECASE)
        if status_match:
            status = status_match.group(1).strip().lower()
            
        return templates.TemplateResponse(
            "briefing_detail.html",
            {
                "request": request, 
                "filename": filename,
                "content": html_content,
                "status": status
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Briefing não encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{filename}/prepare-week")
async def prepare_week(filename: str):
    """
    Retorna os dados default extraídos do briefing para preencher o modal de geração.
    """
    try:
        data = service.prepare_week_from_briefing(filename)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{filename}/generate-week")
async def generate_week(filename: str, request: Request):
    """
    Gera a semana editorial a partir do briefing aprovado.
    """
    try:
        data = await request.json()
    except:
        data = {}
        
    if not data.get("confirm"):
        raise HTTPException(status_code=400, detail="Confirmação necessária para gerar a semana.")
        
    try:
        result = service.generate_week_from_briefing(filename, data)
        return result
    except ValueError as e:
        print(f"Erro de validação na geração da semana: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Erro na geração da semana: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from pydantic import BaseModel
class ApproveBriefingRequest(BaseModel):
    confirm: bool = False

class EditBriefingRequest(BaseModel):
    content: str
    confirm: bool = False

@router.get("/{filename}/edit", response_class=HTMLResponse)
async def edit_briefing_view(request: Request, filename: str):
    try:
        raw_content = service.read_briefing(filename)
        return templates.TemplateResponse(
            "briefing_edit.html",
            {
                "request": request, 
                "filename": filename,
                "content": raw_content
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Briefing não encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{filename}/edit")
async def edit_briefing_action(filename: str, payload: EditBriefingRequest, request: Request):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmação necessária.")
    
    result = service.edit_briefing(filename, payload.content, confirm=payload.confirm)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

@router.post("/{filename}/approve")
async def approve_briefing_action(filename: str, payload: ApproveBriefingRequest, request: Request):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmação necessária.")
        
    result = service.approve_briefing(filename, confirm=payload.confirm)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

@router.post("/{filename}/archive")
async def archive_briefing_action(filename: str, payload: ApproveBriefingRequest, request: Request):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmação necessária.")
        
    result = service.archive_briefing(filename, confirm=payload.confirm)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result
