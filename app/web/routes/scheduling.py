from fastapi import APIRouter, Request, HTTPException
from app.core.brandos_service import BrandOSService

router = APIRouter(prefix="/schedule", tags=["scheduling"])
service = BrandOSService()

@router.post("/post/{item_id}")
async def schedule_post(item_id: str, request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Formato JSON inválido.")
        
    confirm = data.get("confirm", False)
    scheduled_date = data.get("scheduled_date")
    scheduled_time = data.get("scheduled_time")
    
    if not scheduled_date or not scheduled_time:
        raise HTTPException(status_code=400, detail="Data e horário de agendamento são obrigatórios.")
        
    try:
        result = service.schedule_post(item_id, scheduled_date, scheduled_time, confirm)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/post/{item_id}/reschedule")
async def reschedule_post(item_id: str, request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Formato JSON inválido.")
        
    confirm = data.get("confirm", False)
    scheduled_date = data.get("scheduled_date")
    scheduled_time = data.get("scheduled_time")
    
    if not scheduled_date or not scheduled_time:
        raise HTTPException(status_code=400, detail="Data e horário de agendamento são obrigatórios.")
        
    try:
        result = service.reschedule_post(item_id, scheduled_date, scheduled_time, confirm)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/post/{item_id}/unschedule")
async def unschedule_post(item_id: str, request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Formato JSON inválido.")
        
    confirm = data.get("confirm", False)
    
    try:
        result = service.unschedule_post(item_id, confirm)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
