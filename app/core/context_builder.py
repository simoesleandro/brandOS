import os
from app.core.file_reader import read_markdown_file, read_all_markdowns_in_dir
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ContextBuilder:
    def __init__(self, base_dir: str = "."):
        self.knowledge_dir = os.path.join(base_dir, "data", "knowledge")
        self.inbox_dir = os.path.join(base_dir, "data", "inbox")
        
    def build_knowledge_base_context(self) -> str:
        """Agrupa todos os documentos de base de conhecimento em uma única string estruturada."""
        logger.info("Construindo contexto da base de conhecimento...")
        knowledge_files = read_all_markdowns_in_dir(self.knowledge_dir)
        
        context_parts = ["# BASE DE CONHECIMENTO\n"]
        
        for filename, content in knowledge_files.items():
            if content.strip():
                context_parts.append(f"## {filename}\n{content}\n")
                
        return "\n".join(context_parts)
    
    def get_weekly_briefing(self) -> str:
        """Lê o briefing da semana."""
        briefing_path = os.path.join(self.inbox_dir, "briefing-da-semana.md")
        return read_markdown_file(briefing_path)
    
    def build_full_context(self) -> str:
        """Monta o super contexto unindo a base de conhecimento e o briefing."""
        kb_context = self.build_knowledge_base_context()
        briefing = self.get_weekly_briefing()
        
        if not briefing.strip():
            logger.warning("Briefing da semana vazio ou não encontrado.")
            
        full_context = f"{kb_context}\n# BRIEFING DA SEMANA\n{briefing}"
        return full_context
