import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

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
from app.web.routes import dashboard, generations, publications, projects, history, settings

# Registra os roteadores
app.include_router(dashboard.router)
app.include_router(generations.router)
app.include_router(publications.router)
app.include_router(projects.router)
app.include_router(history.router)
app.include_router(settings.router)

if __name__ == "__main__":
    print("Iniciando BrandOS Web Console em http://localhost:8000")
    uvicorn.run("app.web.server:app", host="127.0.0.1", port=8000, reload=True)
