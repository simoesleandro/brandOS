from app.core.llm_client import LLMClient
from app.prompts.system_prompts import EDITOR_SYSTEM_PROMPT
from app.prompts.workflow_prompts import EDITOR_REVIEW_PROMPT

class EditorAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, draft_post: str, super_context: str) -> str:
        prompt = EDITOR_REVIEW_PROMPT.format(draft=draft_post, context=super_context)
        return self.llm.generate_content(EDITOR_SYSTEM_PROMPT, prompt)
