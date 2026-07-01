from app.core.llm_client import LLMClient
from app.prompts.system_prompts import COPYWRITER_SYSTEM_PROMPT
from app.prompts.workflow_prompts import COPYWRITER_POST_PROMPT

class CopywriterAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, super_context: str, weekly_plan: str, post_id: str) -> str:
        prompt = COPYWRITER_POST_PROMPT.format(
            context=super_context, 
            plan=weekly_plan, 
            post_id=post_id
        )
        return self.llm.generate_content(COPYWRITER_SYSTEM_PROMPT, prompt)
