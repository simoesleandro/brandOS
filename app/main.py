import sys
import os

# Ajusta o PYTHONPATH para que as importações absolutas a partir de "app" funcionem
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.workflows.weekly_workflow import run_weekly_workflow
from app.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    if len(sys.argv) < 2:
        print("Uso: python app/main.py [comando]")
        print("Comandos disponíveis:")
        print("  weekly - Executa o workflow de criação de conteúdo da semana.")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "weekly":
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            run_weekly_workflow(base_dir=base_dir)
        except Exception as e:
            logger.error(f"Ocorreu um erro fatal na execução do workflow: {e}", exc_info=True)
            sys.exit(1)
    else:
        print(f"Comando desconhecido: {command}")
        print("Comandos disponíveis:")
        print("  weekly - Executa o workflow de criação de conteúdo da semana.")
        sys.exit(1)

if __name__ == "__main__":
    main()
