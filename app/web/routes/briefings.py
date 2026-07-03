from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.brandos_service import BrandOSService
import os

router = APIRouter(prefix="/briefings", tags=["briefings"])

# Diretório base do projeto (na raiz brandos)
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
templates = Jinja2Templates(directory=os.path.join(base_dir, "app", "web", "templates"))

# Instancia o serviço
service = BrandOSService(base_dir)

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
        return templates.TemplateResponse(
            "briefing_detail.html",
            {
                "request": request, 
                "filename": filename,
                "content": html_content
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
