import os
from app.core.llm_client import LLMClient
from app.core.context_builder import ContextBuilder
from app.core.file_writer import save_markdown_file
from app.core.output_validator import validate_or_retry_generation
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

def run_weekly_workflow(base_dir: str = "."):
    logger.info("Iniciando o Weekly Workflow...")
    
    # 1. Configurar cliente LLM e Contexto
    try:
        llm = LLMClient()
    except Exception as e:
        logger.error("Falha ao inicializar LLMClient. Verifique seu .env.")
        raise
        
    context_builder = ContextBuilder(base_dir=base_dir)
    super_context = context_builder.build_full_context()
    
    # 2. Inicializar Agentes
    cmo = CMOAgent(llm)
    strategist = ContentStrategistAgent(llm)
    copywriter = CopywriterAgent(llm)
    editor = EditorAgent(llm)
    designer = DesignerAgent(llm)
    networking = NetworkingAgent(llm)
    publisher = PublisherAgent(llm)
    
    # Configurar pasta de saída
    output_dir = os.path.join(base_dir, "data", "generated", get_weekly_folder_name())
    
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
        final_text = validate_or_retry_generation(lambda: editor.run(draft, super_context), post["file"])
        
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
    
    logger.info(f"Weekly Workflow concluído! Arquivos gerados em {output_dir}")
