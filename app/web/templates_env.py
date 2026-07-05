import os
from fastapi.templating import Jinja2Templates

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "web", "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

def translate_status(status):
    mapping = {
        "published": "Publicado",
        "discarded": "Descartado",
        "waiting_24h_metrics": "Aguardando métricas 24h",
        "waiting_48h_metrics": "Aguardando métricas 48h",
        "waiting_7d_metrics": "Aguardando métricas 7 dias",
        "metrics_imported": "Métricas importadas",
        "analysis_generated": "Análise gerada",
        "completed": "Concluído",
        "draft": "Rascunho",
        "generated": "Gerado",
        "edited": "Editado",
        "approved": "Aprovado",
        "scheduled": "Agendado",
        "publishing_ready": "Pronto para publicar",
        "used_as_asset": "Asset vinculado",
        "ready_to_publish": "Pronto para publicar",
        "reviewed": "Revisado",
        "needs_revision": "Revisar",
        "skipped": "Ignorado",
        "analyzed": "Analisado",
        "partially_published": "Parcialmente Publicado",
        "in_progress": "Em Andamento",
        "pending": "Pendente",
        "missing": "Ausente"
    }
    return mapping.get(status, status) if status else status

templates.env.filters["translate_status"] = translate_status
