from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.core.brandos_service import BrandOSService
from app.web.templates_env import templates
from datetime import datetime, timedelta

router = APIRouter()
service = BrandOSService()

@router.get("/calendar")
@router.get("/editorial-calendar")
async def get_calendar(request: Request):
    items = service.get_editorial_calendar()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    next_7_days = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 8)]
    
    groups = {
        "hoje": [],
        "proximos_7_dias": [],
        "sem_data": [],
        "publicadas": [],
        "futuras": [],
        "passadas": [],
        "descartadas": []
    }
    
    for item in items:
        status = item.get("status")
        if status == "discarded":
            groups["descartadas"].append(item)
            continue
            
        if status == "published":
            groups["publicadas"].append(item)
            continue
            
        sched = item.get("scheduled_for") or item.get("scheduled_date")
        if not sched:
            groups["sem_data"].append(item)
        elif sched == today_str:
            groups["hoje"].append(item)
        elif sched in next_7_days:
            groups["proximos_7_dias"].append(item)
        else:
            if sched > next_7_days[-1]:
                groups["futuras"].append(item)
            else:
                groups["passadas"].append(item)

    # Sort each group by scheduled_for then priority/status
    def sort_group(group_list):
        priority_map = {"alta": 1, "high": 1, "normal": 2, "baixa": 3, "low": 3}
        group_list.sort(key=lambda x: (
            x.get("scheduled_for") or "9999-99-99",
            priority_map.get(str(x.get("priority")).lower(), 2),
            x.get("status")
        ))
    
    for k in groups.keys():
        sort_group(groups[k])
        
    counts = {
        "agendadas": sum(1 for i in items if (i.get("scheduled_for") or i.get("scheduled_date")) and i.get("status") != "published"),
        "prontas": sum(1 for i in items if i.get("status") == "ready_to_publish"),
        "publicadas": len(groups.get("publicadas", [])),
        "pendentes": sum(1 for i in items if i.get("status") in ("draft", "generated")),
        "revisao": sum(1 for i in items if i.get("status") == "needs_revision")
    }
    
    return templates.TemplateResponse("calendar.html", {
        "request": request,
        "groups": groups,
        "counts": counts
    })

@router.post("/calendar/cmo-recommendation")
async def generate_cmo_recommendation(request: Request):
    print("[CMO] Iniciando recomendação")
    try:
        recommendation_text = service.generate_cmo_recommendation()
        return {
            "status": "success",
            "recommendation": recommendation_text
        }
    except Exception as e:
        error_code = str(e)
        return {
            "status": "error",
            "message": "Não foi possível gerar a recomendação agora.",
            "error_code": error_code if error_code in [
                "gemini_api_key_missing", 
                "gemini_client_error", 
                "gemini_generation_error", 
                "context_build_error", 
                "save_file_error"
            ] else "unknown_error"
        }

class SaveBriefingRequest(BaseModel):
    recommendation: str

@router.post("/calendar/save-briefing")
async def save_briefing(request: SaveBriefingRequest):
    try:
        path = service.save_cmo_recommendation_as_briefing(request.recommendation)
        return {
            "status": "success",
            "message": "Briefing salvo com sucesso.",
            "path": path
        }
    except Exception as e:
        print(f"[CMO][ERROR] Falha ao salvar briefing no backend: {repr(e)}")
        return {
            "status": "error",
            "message": "Não foi possível salvar o briefing."
        }
