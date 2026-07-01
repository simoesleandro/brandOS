import os
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)

def ensure_directory_exists(directory: str):
    """Garante que o diretório existe, criando se necessário."""
    Path(directory).mkdir(parents=True, exist_ok=True)

def save_markdown_file(directory: str, filename: str, content: str) -> str:
    """
    Salva um conteúdo em formato Markdown no diretório e nome especificados.
    Retorna o caminho completo do arquivo salvo.
    """
    ensure_directory_exists(directory)
    filepath = os.path.join(directory, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Arquivo salvo com sucesso: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo {filepath}: {e}")
        raise
