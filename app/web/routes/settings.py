from fastapi import APIRouter, Request
from app.core.brandos_service import BrandOSService
from app.web.templates_env import templates
from dotenv import load_dotenv
import os

router = APIRouter(prefix="/settings", tags=["settings"])
service = BrandOSService()

@router.get("/")
async def get_settings(request: Request):
    load_dotenv()
    api_key_status = "Configurada" if os.getenv("GEMINI_API_KEY") else "Não configurada"
    model_name = os.getenv("BRANDOS_MODEL", "gemini-2.5-flash")
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "api_key_status": api_key_status,
        "model_name": model_name,
        "knowledge_dir": service.knowledge_dir,
        "registry_dir": service.registry_dir,
        "generated_dir": service.generated_dir
    })
