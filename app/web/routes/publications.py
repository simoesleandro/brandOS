from typing import List
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse
from fastapi import HTTPException
from pathlib import Path
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
            
        # In-memory metrics migration for the view
        current_metrics = item.get("metrics", {})
        if current_metrics:
            import uuid
            if "latest" not in current_metrics and "snapshots" not in current_metrics:
                # Flat legacy structure
                legacy = dict(current_metrics)
                legacy["id"] = legacy.get("id") or str(uuid.uuid4())
                legacy["label"] = "inicial"
                cap_date = legacy.get("captured_at")
                if not cap_date:
                    cap_date = item.get("published_at", "")[:10] if item.get("published_at") else ""
                legacy["captured_at"] = cap_date
                item["metrics"] = {
                    "latest": legacy,
                    "snapshots": [legacy]
                }
            elif "latest" in current_metrics and not current_metrics.get("snapshots"):
                # Has latest but empty snapshots
                legacy = dict(current_metrics["latest"])
                legacy["id"] = legacy.get("id") or str(uuid.uuid4())
                legacy["label"] = "inicial"
                if not legacy.get("captured_at"):
                    legacy["captured_at"] = item.get("published_at", "")[:10] if item.get("published_at") else ""
                current_metrics["snapshots"] = [legacy]
                item["metrics"] = current_metrics
                
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
    files: List[UploadFile] = File(None),
    file: UploadFile = File(None),
    asset_category: str = Form(...),
    asset_role: str = Form("")
):
    import traceback
    try:
        upload_files = files if files else ([file] if file else [])
        
        # Filtra elementos nulos ou vazios
        valid_files = [f for f in upload_files if f and f.filename]
        
        if not valid_files:
            print(f"[{folder_id}/{item_id}] Upload bloqueado: Nenhum arquivo selecionado.")
        else:
            for f in valid_files:
                file_content = await f.read()
                content_type = f.content_type
                print(f"[{folder_id}/{item_id}] Processando upload: {f.filename} ({content_type}) para categoria {asset_category}")
                service.upload_item_asset(folder_id, item_id, f.filename, file_content, asset_category, asset_role)
                print(f"[{folder_id}/{item_id}] Upload finalizado: {f.filename}")
                
    except Exception as e:
        print(f"!!! ERRO FATAL NO UPLOAD [{folder_id}/{item_id}] !!!")
        print(f"Categoria: {asset_category} | Role: {asset_role}")
        traceback.print_exc()
        
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


@router.post("/{folder_id}/item/{item_id}/assets/import-prompt")
async def import_prompt(
    request: Request, 
    folder_id: str, 
    item_id: str, 
    source_file: str = Form(...)
):
    try:
        service.import_recommended_prompt(folder_id, item_id, source_file)
    except Exception as e:
        print(f"Erro ao importar prompt: {e}")
    referer = request.headers.get("referer")
    return RedirectResponse(url=referer or f"/publications/{folder_id}/item/{item_id}", status_code=303)

@router.post("/{folder_id}/item/{item_id}/metrics")
async def update_metrics(
    request: Request,
    folder_id: str,
    item_id: str,
    linkedin_url: str = Form(""),
    published_at: str = Form(""),
    label: str = Form("inicial"),
    custom_label: str = Form(""),
    captured_at: str = Form(""),
    impressions: str = Form("0"),
    reach: str = Form("0"),
    reactions: str = Form("0"),
    comments: str = Form("0"),
    shares: str = Form("0"),
    saves: str = Form("0"),
    sends: str = Form("0"),
    profile_views: str = Form("0"),
    followers_gained: str = Form("0"),
    notes: str = Form("")
):
    metrics_data = {
        "linkedin_url": linkedin_url,
        "published_at": published_at,
        "label": label,
        "custom_label": custom_label,
        "captured_at": captured_at,
        "impressions": impressions,
        "reach": reach,
        "reactions": reactions,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "sends": sends,
        "profile_views": profile_views,
        "followers_gained": followers_gained,
        "notes": notes
    }
    
    import traceback
    try:
        service.add_metrics_snapshot(folder_id, item_id, metrics_data)
    except Exception as e:
        print(f"!!! ERRO FATAL AO SALVAR MÉTRICAS [{folder_id}/{item_id}] !!!")
        traceback.print_exc()
        
    referer = request.headers.get("referer")
    redirect_url = referer if referer else f"/publications/{folder_id}/item/{item_id}"
    return RedirectResponse(url=redirect_url, status_code=303)

@router.post("/{folder_id}/item/{item_id}/metrics/generate-analysis")
async def generate_metrics_analysis(
    request: Request,
    folder_id: str,
    item_id: str,
    label: str = Form("inicial"),
    custom_label: str = Form(""),
    captured_at: str = Form(""),
    impressions: str = Form("0"),
    reach: str = Form("0"),
    reactions: str = Form("0"),
    comments: str = Form("0"),
    shares: str = Form("0"),
    saves: str = Form("0"),
    sends: str = Form("0"),
    profile_views: str = Form("0"),
    followers_gained: str = Form("0")
):
    from fastapi.responses import JSONResponse
    import traceback
    try:
        try:
            imp = int(impressions or 0)
            rea = int(reach or 0)
            total_eng = (int(reactions or 0) + int(comments or 0) + int(shares or 0) + 
                         int(saves or 0) + int(sends or 0))
        except ValueError:
            return JSONResponse({"status": "error", "message": "Valores numéricos inválidos."}, status_code=400)
            
        if imp == 0 and rea == 0 and total_eng == 0:
            return JSONResponse({"status": "error", "message": "Preencha as métricas antes de gerar a análise."})
            
        snapshot_data = {
            "label": label,
            "custom_label": custom_label,
            "captured_at": captured_at,
            "impressions": impressions,
            "reach": reach,
            "reactions": reactions,
            "comments": comments,
            "shares": shares,
            "saves": saves,
            "sends": sends,
            "profile_views": profile_views,
            "followers_gained": followers_gained,
            "total_engagements": total_eng,
        }
        
        analysis = service.generate_snapshot_analysis(folder_id, item_id, snapshot_data)
        return JSONResponse({"status": "success", "analysis": analysis})
    except Exception as e:
        print(f"!!! ERRO AO GERAR ANÁLISE IA [{folder_id}/{item_id}] !!!")
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": "Não foi possível gerar a análise agora. Você ainda pode preencher a nota manualmente."})

@router.post("/{folder_id}/item/{item_id}/metrics/import-linkedin")
async def import_linkedin_metrics(
    request: Request,
    folder_id: str,
    item_id: str,
    file: UploadFile = File(...)
):
    import os
    import tempfile
    import traceback
    from fastapi.responses import JSONResponse
    
    filename = file.filename
    if not (filename.lower().endswith('.xlsx') or filename.lower().endswith('.csv')):
        return JSONResponse({"status": "error", "message": "Formato inválido. Apenas arquivos .xlsx e .csv são suportados."})
        
    try:
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
            tmp_path = tmp.name
            content = await file.read()
            tmp.write(content)
            
        try:
            extracted_metrics = service.import_linkedin_analytics(folder_id, item_id, tmp_path, filename)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
        # Calculate derived metrics again to ensure exact formatting requested
        imp = extracted_metrics.get("impressions", 0)
        reach = extracted_metrics.get("reach", 0)
        total_eng = extracted_metrics.get("total_engagements", 0)
        profile_views = extracted_metrics.get("profile_views", 0)
        
        eng_rate_imp = round((total_eng / imp * 100), 2) if imp > 0 else 0
        eng_rate_reach = round((total_eng / reach * 100), 2) if reach > 0 else 0
        profile_view_rate = round((profile_views / reach * 100), 2) if reach > 0 else 0
        
        extracted_metrics["engagement_rate_by_impressions"] = eng_rate_imp
        extracted_metrics["engagement_rate_by_reach"] = eng_rate_reach
        extracted_metrics["profile_view_rate_by_reach"] = profile_view_rate
        
        return JSONResponse({
            "status": "success",
            "metrics": extracted_metrics,
            "source": {
                "filename": filename
            }
        })
    except Exception as e:
        print(f"!!! ERRO AO IMPORTAR LINKEDIN ANALYTICS [{folder_id}/{item_id}] !!!")
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e) if "O arquivo foi lido" in str(e) else "Não foi possível interpretar o arquivo do LinkedIn."})

@router.post("/{folder_id}/item/{item_id}/assets/delete")
async def delete_asset(
    request: Request,
    folder_id: str,
    item_id: str,
    category: str = Form(...),
    filename: str = Form(...)
):
    import traceback
    try:
        service.delete_item_asset(folder_id, item_id, category, filename)
    except Exception as e:
        print(f"!!! ERRO FATAL AO DELETAR ASSET [{folder_id}/{item_id}] !!!")
        print(f"Categoria: {category} | Filename: {filename}")
        traceback.print_exc()
        
    referer = request.headers.get("referer")
    return RedirectResponse(url=referer or f"/publications/{folder_id}/item/{item_id}", status_code=303)

@router.post("/{folder_id}/item/{item_id}/assets/delete-prompt")
async def delete_prompt(
    request: Request,
    folder_id: str,
    item_id: str,
    prompt_id: str = Form(None),
    prompt_index: int = Form(None)
):
    import traceback
    try:
        service.delete_item_prompt(folder_id, item_id, prompt_id, prompt_index)
    except Exception as e:
        print(f"!!! ERRO FATAL AO DELETAR PROMPT [{folder_id}/{item_id}] !!!")
        print(f"Prompt ID: {prompt_id} | Index: {prompt_index}")
        traceback.print_exc()
        
    referer = request.headers.get("referer")
    return RedirectResponse(url=referer or f"/publications/{folder_id}/item/{item_id}", status_code=303)


@router.post("/{folder_id}/item/{item_id}/schedule")
async def update_schedule(
    request: Request,
    folder_id: str,
    item_id: str,
    channel: str = Form("linkedin"),
    scheduled_for: str = Form(""),
    scheduled_time: str = Form(""),
    priority: str = Form("normal"),
    schedule_notes: str = Form("")
):
    import traceback
    try:
        schedule_data = {
            "channel": channel,
            "scheduled_for": scheduled_for,
            "scheduled_time": scheduled_time,
            "priority": priority,
            "schedule_notes": schedule_notes
        }
        print(f"[BrandOS] Salvando agendamento {folder_id} {item_id} {schedule_data}")
        service.update_item_schedule(folder_id, item_id, schedule_data)
        print("[BrandOS] Agendamento salvo com sucesso")
    except Exception as e:
        print(f"!!! ERRO FATAL AO SALVAR AGENDAMENTO [{folder_id}/{item_id}] !!!")
        traceback.print_exc()
        
    referer = request.headers.get("referer")
    base_url = referer if referer else f"/publications/{folder_id}/item/{item_id}"
    
    # Remove any existing msg param
    if "?" in base_url:
        base_url = base_url.split("?")[0]
        
    return RedirectResponse(url=f"{base_url}?msg=schedule_saved", status_code=303)
