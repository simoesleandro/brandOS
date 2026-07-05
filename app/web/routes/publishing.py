from fastapi import APIRouter, Request, HTTPException
from app.core.brandos_service import BrandOSService
from app.web.templates_env import templates
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["publishing"])
service = BrandOSService()

class PublishReadyRequest(BaseModel):
    confirm: bool

class PublishDoneRequest(BaseModel):
    confirm: bool
    published_url: Optional[str] = None
    published_at: Optional[str] = None

class PublishUndoRequest(BaseModel):
    confirm: bool
    reason: Optional[str] = None

@router.get("/publish/post/{item_id}")
async def publish_assistant(item_id: str, request: Request):
    try:
        data = service.get_publication_assistant(item_id)
        return templates.TemplateResponse("publish_assistant.html", {
            "request": request,
            "assistant_data": data,
            "error": None
        })
    except ValueError as e:
        return templates.TemplateResponse("publish_assistant.html", {
            "request": request,
            "assistant_data": None,
            "error": str(e)
        })

@router.post("/publish/post/{item_id}/mark-ready")
async def mark_post_ready(item_id: str, payload: PublishReadyRequest):
    try:
        res = service.mark_post_publishing_ready(item_id, payload.confirm)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/publish/post/{item_id}/mark-published")
async def mark_post_published(item_id: str, payload: PublishDoneRequest):
    try:
        res = service.mark_post_published(item_id, payload.confirm, payload.published_url, payload.published_at)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/publish/post/{item_id}/undo-published")
async def undo_post_published(item_id: str, payload: PublishUndoRequest):
    try:
        res = service.undo_post_published(item_id, payload.confirm, payload.reason)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
