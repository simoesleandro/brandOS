import os
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)

def read_markdown_file(filepath: str) -> str:
    """Lê e retorna o conteúdo de um arquivo Markdown."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"Arquivo não encontrado: {filepath}")
        return ""
    except Exception as e:
        logger.error(f"Erro ao ler o arquivo {filepath}: {e}")
        return ""

def read_all_markdowns_in_dir(directory: str) -> dict[str, str]:
    """
    Lê todos os arquivos .md em um diretório e retorna um dicionário
    onde a chave é o nome do arquivo e o valor é o conteúdo.
    """
    contents = {}
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        logger.warning(f"Diretório de conhecimento não encontrado: {directory}")
        return contents

    for filepath in dir_path.glob("*.md"):
        contents[filepath.name] = read_markdown_file(str(filepath))
        
    return contents
