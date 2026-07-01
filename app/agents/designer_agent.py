from app.core.llm_client import LLMClient
from app.prompts.system_prompts import DESIGNER_SYSTEM_PROMPT
from app.prompts.workflow_prompts import DESIGNER_CAROUSEL_PROMPT, DESIGNER_IMAGE_PROMPTS_PROMPT

class DesignerAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate_carousel(self, weekly_plan: str) -> str:
        prompt = DESIGNER_CAROUSEL_PROMPT.format(plan=weekly_plan)
        return self.llm.generate_content(DESIGNER_SYSTEM_PROMPT, prompt)
        
    def generate_image_prompts(self, weekly_plan: str) -> str:
        prompt = DESIGNER_IMAGE_PROMPTS_PROMPT.format(plan=weekly_plan)
        return self.llm.generate_content(DESIGNER_SYSTEM_PROMPT, prompt)
