from app.core.llm_client import LLMClient
from app.prompts.system_prompts import NETWORKING_SYSTEM_PROMPT
from app.prompts.workflow_prompts import NETWORKING_PLAN_PROMPT

class NetworkingAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, super_context: str) -> str:
        prompt = NETWORKING_PLAN_PROMPT.format(context=super_context)
        return self.llm.generate_content(NETWORKING_SYSTEM_PROMPT, prompt)
