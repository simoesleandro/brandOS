from app.core.llm_client import LLMClient
from app.prompts.system_prompts import PUBLISHER_SYSTEM_PROMPT
from app.prompts.workflow_prompts import PUBLISHER_COMMENT_PROMPT, PUBLISHER_INSTRUCTIONS_PROMPT

class PublisherAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate_comments(self, super_context: str, plan: str) -> str:
        """Gera o primeiro comentário recomendado para todos os posts da semana."""
        prompt = PUBLISHER_COMMENT_PROMPT.format(
            context=super_context,
            plan=plan
        )
        return self.llm.generate_content(PUBLISHER_SYSTEM_PROMPT, prompt)

    def generate_instructions(self, super_context: str, plan: str, comments: str) -> str:
        """Gera as instruções e diretrizes finais de publicação da semana."""
        prompt = PUBLISHER_INSTRUCTIONS_PROMPT.format(
            context=super_context,
            plan=plan,
            comments=comments
        )
        return self.llm.generate_content(PUBLISHER_SYSTEM_PROMPT, prompt)
