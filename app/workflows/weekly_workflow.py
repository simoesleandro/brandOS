import json
import os
import re
import shutil
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from app.core.llm_client import LLMClient
from app.core.context_builder import ContextBuilder
from app.core.file_writer import save_markdown_file
from app.core.output_validator import validate_or_retry_generation
from app.core.text_quality import is_linkedin_post_text_quality_ok
from app.utils.logger import get_logger
from app.utils.dates import get_weekly_folder_name
from app.prompts.workflow_prompts import CHECKLIST_TEMPLATE

from app.agents.cmo_agent import CMOAgent
from app.agents.content_strategist_agent import ContentStrategistAgent
from app.agents.copywriter_agent import CopywriterAgent
from app.agents.editor_agent import EditorAgent
from app.agents.designer_agent import DesignerAgent
from app.agents.networking_agent import NetworkingAgent
from app.agents.publisher_agent import PublisherAgent

logger = get_logger(__name__)


@dataclass
class WeeklyGenerationRequest:
    briefing_content: str
    project: str
    theme: str
    start_date: str
    frequency: str = "Segunda / Quarta / Sexta"
    source_briefing_file: str | None = None
    source_recommendation_id: str | None = None


EXPECTED_WEEKLY_FILES = [
    "01-diagnostico-cmo.md",
    "02-plano-semanal.md",
    "03-post-segunda.md",
    "04-post-quarta.md",
    "05-post-sexta.md",
    "06-carrossel.md",
    "07-prompts-imagem.md",
    "08-plano-networking.md",
    "09-checklist-publicacao.md",
    "10-comentario-linkedin.md",
    "11-instrucoes-publicacao.md",
]


def run_weekly_workflow(base_dir: str = ".", request: WeeklyGenerationRequest | None = None, llm_client=None):
    logger.info("Iniciando o Weekly Workflow...")
    
    # 1. Configurar cliente LLM e Contexto
    try:
        llm = llm_client or LLMClient()
    except Exception as e:
        logger.error("Falha ao inicializar LLMClient. Verifique seu .env.")
        raise
        
    super_context = _build_super_context(base_dir, request)
    
    # 2. Inicializar Agentes
    cmo = CMOAgent(llm)
    strategist = ContentStrategistAgent(llm)
    copywriter = CopywriterAgent(llm)
    editor = EditorAgent(llm)
    designer = DesignerAgent(llm)
    networking = NetworkingAgent(llm)
    publisher = PublisherAgent(llm)
    
    # Configurar pasta de saída
    folder_name = _build_weekly_folder_name(request)
    output_dir = os.path.join(base_dir, "data", "generated", folder_name)
    if os.path.exists(output_dir):
        folder_name = f"{folder_name}-{datetime.now().strftime('%H%M%S')}"
        output_dir = os.path.join(base_dir, "data", "generated", folder_name)
    
    # === ETAPA 1: CMO ===
    filename = "01-diagnostico-cmo.md"
    diagnosis = validate_or_retry_generation(lambda: cmo.run(super_context), filename)
    logger.info(f"[BrandOS] Salvando {filename}...")
    save_markdown_file(output_dir, filename, diagnosis)
    
    # === ETAPA 2: Estrategista ===
    filename = "02-plano-semanal.md"
    plan = validate_or_retry_generation(lambda: strategist.run(super_context, diagnosis), filename)
    logger.info(f"[BrandOS] Salvando {filename}...")
    save_markdown_file(output_dir, filename, plan)
    
    # === ETAPA 3: Copywriter e Editor ===
    posts = [
        {"id": "Post 1 (Segunda-feira)", "file": "03-post-segunda.md"},
        {"id": "Post 2 (Quarta-feira)", "file": "04-post-quarta.md"},
        {"id": "Post 3 (Sexta-feira)", "file": "05-post-sexta.md"}
    ]
    
    for post in posts:
        # Gera o rascunho
        draft = validate_or_retry_generation(lambda: copywriter.run(super_context, plan, post["id"]), f"{post['file']} (Rascunho)")
        
        # O Editor revisa
        final_text = validate_or_retry_generation(
            lambda: editor.run(draft, super_context),
            post["file"],
            max_retries=2,
            quality_validator=is_linkedin_post_text_quality_ok,
            warning_message="O post pode conter problemas de acentuação em português brasileiro. Revise antes de publicar.",
        )
        
        logger.info(f"[BrandOS] Salvando {post['file']}...")
        save_markdown_file(output_dir, post["file"], final_text)
        
    # === ETAPA 4: Designer ===
    filename = "06-carrossel.md"
    carousel = validate_or_retry_generation(lambda: designer.generate_carousel(plan), filename)
    logger.info(f"[BrandOS] Salvando {filename}...")
    save_markdown_file(output_dir, filename, carousel)
    
    filename = "07-prompts-imagem.md"
    image_prompts = validate_or_retry_generation(lambda: designer.generate_image_prompts(plan), filename)
    logger.info(f"[BrandOS] Salvando {filename}...")
    save_markdown_file(output_dir, filename, image_prompts)
    
    # === ETAPA 5: Networking ===
    filename = "08-plano-networking.md"
    networking_plan = validate_or_retry_generation(lambda: networking.run(super_context), filename)
    logger.info(f"[BrandOS] Salvando {filename}...")
    save_markdown_file(output_dir, filename, networking_plan)
    
    # === ETAPA 6: Checklist ===
    filename = "09-checklist-publicacao.md"
    logger.info(f"[BrandOS] Gerando {filename}...")
    logger.info(f"[BrandOS] Validando {filename}...")
    logger.info(f"[BrandOS] Salvando {filename}...")
    save_markdown_file(output_dir, filename, CHECKLIST_TEMPLATE)
    
    # === ETAPA 7: Publicação (Comentários e Instruções) ===
    filename = "10-comentario-linkedin.md"
    comments = validate_or_retry_generation(lambda: publisher.generate_comments(super_context, plan), filename)
    logger.info(f"[BrandOS] Salvando {filename}...")
    save_markdown_file(output_dir, filename, comments)
    
    filename = "11-instrucoes-publicacao.md"
    instructions = validate_or_retry_generation(lambda: publisher.generate_instructions(super_context, plan, comments), filename)
    logger.info(f"[BrandOS] Salvando {filename}...")
    save_markdown_file(output_dir, filename, instructions)
    
    result = {
        "status": "success",
        "folder": folder_name,
        "output_dir": output_dir,
        "files": EXPECTED_WEEKLY_FILES,
        "item_ids": [],
        "warnings": [],
    }

    if request:
        registry_result = register_generated_week(base_dir, folder_name, request)
        result["item_ids"] = registry_result["item_ids"]
        result["registry_entry_id"] = registry_result["week_id"]

    logger.info(f"Weekly Workflow concluído! Arquivos gerados em {output_dir}")
    return result


def register_generated_week(base_dir: str, folder_name: str, request: WeeklyGenerationRequest) -> dict:
    log_path = os.path.join(base_dir, "data", "registry", "publication-log.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    log_data = []
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                log_data = loaded if isinstance(loaded, list) else []
        except Exception:
            log_data = []

    existing = _find_existing_week(log_data, request)
    if existing:
        return {
            "week_id": existing.get("id"),
            "item_ids": [item.get("item_id") or item.get("id") for item in existing.get("items", [])],
            "idempotent": True,
        }

    now = datetime.now()
    start_dt = datetime.strptime(request.start_date, "%Y-%m-%d")
    planned_days = [
        ("segunda", "03-post-segunda.md", start_dt),
        ("quarta", "04-post-quarta.md", start_dt + timedelta(days=2)),
        ("sexta", "05-post-sexta.md", start_dt + timedelta(days=4)),
    ]

    source = "generated_from_cmo_briefing" if request.source_recommendation_id else "generated_from_briefing"
    item_ids = []
    items = []
    for day, filename, planned_dt in planned_days:
        item_id = f"post-{day}-{now.strftime('%H%M%S')}"
        item_ids.append(item_id)
        item = {
            "id": item_id,
            "item_id": item_id,
            "title": f"Post {day}",
            "type": "linkedin_post",
            "status": "generated",
            "file": f"generated/{folder_name}/{filename}",
            "content_file": f"data/generated/{folder_name}/{filename}",
            "project": request.project,
            "created_at": now.isoformat(),
            "suggested_for": planned_dt.strftime("%Y-%m-%d"),
            "source": source,
            "briefing_file": request.source_briefing_file,
            "source_briefing_file": request.source_briefing_file,
            "source_recommendation_id": request.source_recommendation_id,
            "planned_week_start": request.start_date,
            "planned_day": day,
            "generated_folder": folder_name,
        }
        if request.source_recommendation_id:
            item["generated_from_cmo"] = True
        items.append(item)

    new_week = {
        "id": folder_name,
        "date": request.start_date,
        "project": request.project,
        "theme": request.theme,
        "status": "generated",
        "source": source,
        "source_briefing_file": request.source_briefing_file,
        "source_recommendation_id": request.source_recommendation_id,
        "files": EXPECTED_WEEKLY_FILES,
        "items": items,
    }
    log_data.append(new_week)

    backup_dir = os.path.join(base_dir, "data", "registry", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    if os.path.exists(log_path):
        backup_file = os.path.join(backup_dir, f"publication-log-{now.strftime('%Y%m%d-%H%M%S')}.json")
        shutil.copy2(log_path, backup_file)

    fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(log_path), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, log_path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    return {"week_id": folder_name, "item_ids": item_ids, "idempotent": False}


def _build_super_context(base_dir: str, request: WeeklyGenerationRequest | None) -> str:
    if request is None:
        context_builder = ContextBuilder(base_dir=base_dir)
        return context_builder.build_full_context()

    context_builder = ContextBuilder(base_dir=base_dir)
    kb_context = context_builder.build_knowledge_base_context()
    return f"""{kb_context}
# BRIEFING APROVADO DA SEMANA
Projeto: {request.project}
Tema central: {request.theme}
Data inicial: {request.start_date}
Frequência: {request.frequency}
Briefing de origem: {request.source_briefing_file or 'Não informado'}
Recomendação CMO de origem: {request.source_recommendation_id or 'Não informada'}

{request.briefing_content}
"""


def _build_weekly_folder_name(request: WeeklyGenerationRequest | None) -> str:
    if request is None:
        return get_weekly_folder_name()
    return f"{request.start_date}-semana-{_slugify(request.project)}"


def _find_existing_week(log_data: list, request: WeeklyGenerationRequest) -> dict | None:
    for week in log_data:
        if not isinstance(week, dict):
            continue
        if week.get("source_briefing_file") == request.source_briefing_file and week.get("date") == request.start_date:
            return week
        items = week.get("items", [])
        matching = [
            item for item in items
            if item.get("source_briefing_file") == request.source_briefing_file
            and item.get("planned_week_start") == request.start_date
        ]
        if len(matching) >= 3:
            return week
    return None


def _slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_") or "projeto"
