from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from app.core.brandos_service import BrandOSService

router = APIRouter(prefix="/generated-weeks", tags=["generated-weeks"])
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))
service = BrandOSService()

@router.get("/{folder_name}", response_class=HTMLResponse)
async def get_generated_week(request: Request, folder_name: str):
    try:
        details = service.get_generated_week_details(folder_name)
        return templates.TemplateResponse(
            "generated_week_detail.html",
            {"request": request, "week": details}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{folder_name}/posts/{planned_day}/edit")
async def edit_post(folder_name: str, planned_day: str, request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Formato JSON inválido.")
        
    content = data.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="Conteúdo do post não informado.")
        
    try:
        result = service.edit_generated_post(folder_name, planned_day, content)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{folder_name}/posts/{planned_day}/approve")
async def approve_post(folder_name: str, planned_day: str):
    try:
        result = service.approve_generated_post(folder_name, planned_day)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{folder_name}/approve-week")
async def approve_week(folder_name: str):
    try:
        result = service.approve_generated_week(folder_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
