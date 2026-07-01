import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do .env, caso exista
load_dotenv()

class Config:
    LLM_PROVIDER = os.getenv("BRANDOS_LLM_PROVIDER", "gemini")
    API_KEY = os.getenv("BRANDOS_API_KEY", "")
    MODEL = os.getenv("BRANDOS_MODEL", "gemini-2.5-flash")
    
    # Parâmetros padrão do modelo
    try:
        TEMPERATURE = float(os.getenv("BRANDOS_TEMPERATURE", "0.7"))
    except ValueError:
        TEMPERATURE = 0.7
        
    try:
        MAX_OUTPUT_TOKENS = int(os.getenv("BRANDOS_MAX_OUTPUT_TOKENS", "8192"))
    except ValueError:
        MAX_OUTPUT_TOKENS = 8192

config = Config()
