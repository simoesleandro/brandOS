from fastapi import APIRouter, Request
from app.web.dependencies import get_brandos_service
from app.web.templates_env import templates

router = APIRouter(prefix="/history", tags=["history"])
service = get_brandos_service()

@router.get("/")
async def get_history(request: Request):
    full_history = service.list_history()
    
    editorial_items = []
    technical_items = []
    
    for entry in full_history:
        date = entry.get("date")
        project = entry.get("project")
        items = entry.get("items", [])
        
        # If the entry has no items (like some test entries), treat the entry itself as an item
        if not items:
            items = [entry]
            
        for item in items:
            is_main, _ = service._is_main_publication(item)
            
            # Formata os dados para a view
            row = {
                "date": date or item.get("date") or "Sem data",
                "project": project or item.get("project") or "Desconhecido",
                "format": item.get("type") or entry.get("format") or "Desconhecido",
                "title": item.get("title") or entry.get("title") or "Sem título",
                "status": item.get("status") or entry.get("status") or "unknown",
                "post_publish_tracking_status": item.get("post_publish_tracking_status")
            }
            
            if is_main:
                editorial_items.append(row)
            else:
                technical_items.append(row)
            
    return templates.TemplateResponse("history.html", {
        "request": request,
        "history": editorial_items,
        "technical_history": technical_items
    })
