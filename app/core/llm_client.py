from google import genai
from google.genai import types
from app.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)

class LLMClient:
    def __init__(self):
        if not config.API_KEY:
            logger.error("BRANDOS_API_KEY não encontrada no .env")
            raise ValueError("BRANDOS_API_KEY não configurada.")
        
        self.client = genai.Client(api_key=config.API_KEY)
        self.model_name = config.MODEL
        
        # Desativar filtros de segurança se desejar (opcional), mas vamos usar um config flexível
        self.gen_config = types.GenerateContentConfig(
            temperature=config.TEMPERATURE,
            max_output_tokens=config.MAX_OUTPUT_TOKENS,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ]
        )
        
        logger.info(f"LLMClient inicializado com modelo {self.model_name} usando a nova SDK google-genai")

    def generate_content(self, system_prompt: str, user_prompt: str) -> str:
        """Gera conteúdo usando a API do Gemini."""
        try:
            # Set system instruction for this call
            self.gen_config.system_instruction = system_prompt
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=self.gen_config
            )
            return response.text
        except Exception as e:
            logger.error(f"Erro ao gerar conteúdo na API do Gemini: {e}")
            raise
