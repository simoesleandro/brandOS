import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException
from pathlib import Path

# Configurar diretórios
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")
STATIC_DIR = os.path.join(WEB_DIR, "static")
TEMPLATES_DIR = os.path.join(WEB_DIR, "templates")

# Inicializa o app
app = FastAPI(title="BrandOS Web Console")

# Monta arquivos estáticos se a pasta existir
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Importa as rotas
from app.web.routes import dashboard, generations, publications, projects, history, settings, calendar, briefings, generated_weeks, scheduling, ops, publishing, strategic_memory, cmo_recommendations

# Registra os roteadores
app.include_router(dashboard.router)
app.include_router(generations.router)
app.include_router(publications.router)
app.include_router(projects.router)
app.include_router(history.router)
app.include_router(settings.router)
app.include_router(calendar.router)
app.include_router(briefings.router)
app.include_router(generated_weeks.router)
app.include_router(scheduling.router)
app.include_router(ops.router)
app.include_router(publishing.router)
app.include_router(strategic_memory.router)
app.include_router(cmo_recommendations.router)


@app.get("/assets/{folder_id}/{item_id}/{category}/{filename}")
async def get_asset(folder_id: str, item_id: str, category: str, filename: str):
    valid_categories = {"images", "slides", "pdf", "video", "source", "prompts"}
    if category not in valid_categories:
        raise HTTPException(status_code=404, detail="Categoria inválida")
        
    assets_dir = Path("data/assets").resolve()
    target_path = (assets_dir / f"{folder_id}-{item_id}" / category / filename).resolve()
    
    # Path traversal protection
    if not str(target_path).startswith(str(assets_dir)):
        raise HTTPException(status_code=403, detail="Acesso negado")
        
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        
    return FileResponse(target_path)

if __name__ == "__main__":
    print("Iniciando BrandOS Web Console em http://localhost:8000")
    reload_mode = os.environ.get("BRANDOS_RELOAD", "false").lower() == "true"
    if reload_mode:
        print("Aviso: Executando em modo RELOAD (desenvolvimento).")
        uvicorn.run(
            "app.web.server:app", 
            host="127.0.0.1", 
            port=8000, 
            reload=True,
            reload_excludes=["data", "data/*", "data/assets/*", "data/registry/*", "data/generated/*", "*.json", "__pycache__/*"]
        )
    else:
        print("Modo Estável: Reload desativado para garantir estabilidade no upload.")
        uvicorn.run(
            "app.web.server:app", 
            host="127.0.0.1", 
            port=8000, 
            reload=False
        )
