from app.core.llm_client import LLMClient
from app.prompts.system_prompts import CONTENT_STRATEGIST_SYSTEM_PROMPT
from app.prompts.workflow_prompts import STRATEGIST_PLAN_PROMPT

class ContentStrategistAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, super_context: str, cmo_diagnosis: str) -> str:
        prompt = STRATEGIST_PLAN_PROMPT.format(context=super_context, diagnosis=cmo_diagnosis)
        return self.llm.generate_content(CONTENT_STRATEGIST_SYSTEM_PROMPT, prompt)
