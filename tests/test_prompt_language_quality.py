from app.prompts.system_prompts import COPYWRITER_SYSTEM_PROMPT, EDITOR_SYSTEM_PROMPT
from app.prompts.workflow_prompts import COPYWRITER_POST_PROMPT, EDITOR_REVIEW_PROMPT


def test_copywriter_prompt_requires_brazilian_portuguese_accents():
    prompt = COPYWRITER_SYSTEM_PROMPT + COPYWRITER_POST_PROMPT

    assert "português brasileiro" in prompt
    assert "acentuação correta" in prompt
    assert "concordância" in prompt
    assert "hashtags" in prompt


def test_editor_prompt_rejects_ai_voice_and_missing_accents():
    prompt = EDITOR_SYSTEM_PROMPT + EDITOR_REVIEW_PROMPT

    assert "cara de IA" in prompt
    assert "acentuação correta" in prompt
    assert "concordância verbal" in prompt
    assert "hashtags sem acento" in prompt
