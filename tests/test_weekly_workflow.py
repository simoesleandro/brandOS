import json
import os

from app.workflows.weekly_workflow import (
    EXPECTED_WEEKLY_FILES,
    WeeklyGenerationRequest,
    run_weekly_workflow,
)


class FakeLLM:
    def generate_content(self, system_prompt: str, prompt: str) -> str:
        return (
            "Conteúdo gerado para teste do BrandOS com tamanho suficiente "
            "para passar pela validação do workflow semanal."
        )


def test_weekly_workflow_generates_expected_files_and_registry(mock_env):
    request = WeeklyGenerationRequest(
        briefing_content="# Briefing aprovado\n\nGerar semana editorial real.",
        project="BrandOS",
        theme="Operacao editorial com IA",
        start_date="2026-07-13",
        source_briefing_file="briefing-001.md",
        source_recommendation_id="rec-001",
    )

    result = run_weekly_workflow(mock_env, request=request, llm_client=FakeLLM())

    assert result["status"] == "success"
    assert result["files"] == EXPECTED_WEEKLY_FILES
    assert len(result["item_ids"]) == 3

    folder_path = os.path.join(mock_env, "data", "generated", result["folder"])
    for filename in EXPECTED_WEEKLY_FILES:
        assert os.path.exists(os.path.join(folder_path, filename))

    registry_path = os.path.join(mock_env, "data", "registry", "publication-log.json")
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    generated_week = next(entry for entry in registry if entry["id"] == result["folder"])
    assert generated_week["source"] == "generated_from_cmo_briefing"
    assert generated_week["files"] == EXPECTED_WEEKLY_FILES
    assert [item["planned_day"] for item in generated_week["items"]] == ["segunda", "quarta", "sexta"]
    assert all(item["content_file"].startswith(f"data/generated/{result['folder']}") for item in generated_week["items"])
