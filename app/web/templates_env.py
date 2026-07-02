import os
from fastapi.templating import Jinja2Templates

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "web", "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

def translate_status(status):
    mapping = {
        "draft": "Rascunho",
        "generated": "Gerado",
        "reviewed": "Revisado",
        "ready_to_publish": "Pronto",
        "published": "Publicado",
        "needs_revision": "Revisar",
        "skipped": "Ignorado",
        "analyzed": "Analisado",
        "partially_published": "Parcialmente Publicado",
        "in_progress": "Em Andamento",
        "pending": "Pendente",
        "missing": "Ausente",
        "used_as_asset": "Asset Vinculado"
    }
    return mapping.get(status, status) if status else status

templates.env.filters["translate_status"] = translate_status
