from app.core.llm_client import LLMClient
from app.prompts.system_prompts import CMO_SYSTEM_PROMPT
from app.prompts.workflow_prompts import CMO_DIAGNOSIS_PROMPT

class CMOAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, super_context: str) -> str:
        prompt = CMO_DIAGNOSIS_PROMPT.format(context=super_context)
        return self.llm.generate_content(CMO_SYSTEM_PROMPT, prompt)
