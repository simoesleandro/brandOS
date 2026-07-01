from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from app.core.brandos_service import BrandOSService
from app.web.templates_env import templates

router = APIRouter(prefix="/publications", tags=["publications"])
service = BrandOSService()

@router.get("/")
async def list_publications(request: Request):
    weeks = service.list_generated_weeks()
    return templates.TemplateResponse("publications.html", {
        "request": request,
        "weeks": weeks
    })

@router.get("/{folder_id}")
async def get_publication_detail(request: Request, folder_id: str):
    print(f"Abrindo geração: {folder_id}")
    try:
        details = service.get_generation_details(folder_id)
        if not details:
            return templates.TemplateResponse("error.html", {"request": request, "message": f"Semana ou pasta '{folder_id}' não encontrada no histórico."})
            
        return templates.TemplateResponse("publication_detail.html", {
            "request": request,
            "details": details,
            "folder_id": folder_id
        })
    except Exception as e:
        print(f"Erro interno ao carregar detalhes da semana {folder_id}: {e}")
        return templates.TemplateResponse("error.html", {"request": request, "message": f"Erro interno ao abrir a semana: {str(e)}"})

@router.post("/{folder_id}/item/{item_id}/status")
async def update_item_status(request: Request, folder_id: str, item_id: str, status: str):
    try:
        service.update_item_status(folder_id, item_id, status)
    except Exception as e:
        print(f"Erro ao atualizar status: {e}")
    # Redireciona de volta para onde veio (referer) ou para o detalhe da semana
    referer = request.headers.get("referer")
    if referer:
        return RedirectResponse(url=referer, status_code=303)
    return RedirectResponse(url=f"/publications/{folder_id}", status_code=303)

@router.get("/{folder_id}/item/{item_id}")
async def get_item_detail(request: Request, folder_id: str, item_id: str):
    try:
        details = service.get_generation_details(folder_id)
        if not details:
            return templates.TemplateResponse("error.html", {"request": request, "message": "Semana não encontrada no registro."})
            
        item = next((i for i in details.get("items", []) if i.get("id") == item_id), None)
        if not item:
            return templates.TemplateResponse("error.html", {"request": request, "message": "Peça não encontrada no registro."})
            
        return templates.TemplateResponse("item_detail.html", {
            "request": request,
            "folder_id": folder_id,
            "week_details": details,
            "item": item
        })
    except Exception as e:
        print(f"Erro ao carregar peça: {e}")
        return templates.TemplateResponse("error.html", {"request": request, "message": f"Erro interno ao carregar a peça: {str(e)}"})

@router.post("/{folder_id}/item/{item_id}/assets/init")
async def init_assets(request: Request, folder_id: str, item_id: str):
    try:
        service.init_item_assets(folder_id, item_id)
    except Exception as e:
        print(f"Erro ao inicializar assets: {e}")
    referer = request.headers.get("referer")
    return RedirectResponse(url=referer or f"/publications/{folder_id}/item/{item_id}", status_code=303)

@router.post("/{folder_id}/item/{item_id}/assets/upload")
async def upload_asset(
    request: Request, 
    folder_id: str, 
    item_id: str, 
    file: UploadFile = File(...), 
    asset_category: str = Form(...),
    asset_role: str = Form("")
):
    try:
        content = await file.read()
        service.upload_item_asset(folder_id, item_id, file.filename, content, asset_category, asset_role)
    except Exception as e:
        print(f"Erro ao enviar asset: {e}")
    referer = request.headers.get("referer")
    return RedirectResponse(url=referer or f"/publications/{folder_id}/item/{item_id}", status_code=303)

@router.post("/{folder_id}/item/{item_id}/assets/prompt")
async def add_prompt(
    request: Request, 
    folder_id: str, 
    item_id: str, 
    prompt_text: str = Form(...)
):
    try:
        service.add_item_asset_prompt(folder_id, item_id, prompt_text)
    except Exception as e:
        print(f"Erro ao adicionar prompt: {e}")
    referer = request.headers.get("referer")
    return RedirectResponse(url=referer or f"/publications/{folder_id}/item/{item_id}", status_code=303)
