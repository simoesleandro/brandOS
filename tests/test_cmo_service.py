import json
import os


def setup_cmo_index(base_dir):
    cmo_dir = os.path.join(base_dir, "data", "generated", "cmo-recommendations")
    os.makedirs(cmo_dir, exist_ok=True)

    rec_path = os.path.join(cmo_dir, "rec-active.md")
    with open(rec_path, "w", encoding="utf-8") as f:
        f.write("# Recomendacao ativa")

    index_path = os.path.join(cmo_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({
            "recommendations": [
                {
                    "id": "rec-active",
                    "generated_at": "2026-07-06T10:00:00-0300",
                    "file": "data/generated/cmo-recommendations/rec-active.md",
                    "status": "active",
                    "source_posts_count": 2,
                },
                {
                    "id": "rec-archived",
                    "generated_at": "2026-07-05T10:00:00-0300",
                    "file": "data/generated/cmo-recommendations/rec-archived.md",
                    "status": "archived",
                },
            ]
        }, f)


def test_cmo_service_lists_active_and_archived(cmo_service, mock_env):
    setup_cmo_index(mock_env)

    active, archived, error = cmo_service.list_recommendations()

    assert error is None
    assert [r["id"] for r in active] == ["rec-active"]
    assert [r["id"] for r in archived] == ["rec-archived"]
    assert active[0]["source_posts_count"] == 2


def test_cmo_service_reads_recommendation_markdown(cmo_service, mock_env):
    setup_cmo_index(mock_env)

    recommendation, markdown = cmo_service.read_recommendation_markdown("rec-active")

    assert recommendation["id"] == "rec-active"
    assert markdown == "# Recomendacao ativa"


def test_cmo_service_archives_recommendation(cmo_service, mock_env):
    setup_cmo_index(mock_env)

    result = cmo_service.archive_cmo_recommendation("rec-active", True)

    assert result["status"] == "success"

    active, archived, error = cmo_service.list_recommendations()
    assert error is None
    assert active == []
    assert {r["id"] for r in archived} == {"rec-active", "rec-archived"}


def test_cmo_service_builds_actionable_inbox(cmo_service, mock_env):
    cmo_dir = os.path.join(mock_env, "data", "generated", "cmo-recommendations")
    os.makedirs(cmo_dir, exist_ok=True)
    index_path = os.path.join(cmo_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({
            "recommendations": [
                {
                    "id": "rec-old",
                    "generated_at": "2026-07-05T10:00:00-0300",
                    "file": "data/generated/cmo-recommendations/rec-old.md",
                    "status": "draft_recommendation",
                },
                {
                    "id": "rec-new",
                    "generated_at": "2026-07-06T10:00:00-0300",
                    "file": "data/generated/cmo-recommendations/rec-new.md",
                    "status": "draft_recommendation",
                },
                {
                    "id": "rec-new",
                    "generated_at": "2026-07-06T10:00:00-0300",
                    "file": "data/generated/cmo-recommendations/rec-new.md",
                    "status": "draft_recommendation",
                },
                {
                    "id": "rec-used",
                    "generated_at": "2026-07-04T10:00:00-0300",
                    "file": "data/generated/cmo-recommendations/rec-used.md",
                    "status": "briefing_created",
                    "briefing_filename": "briefing.md",
                },
            ]
        }, f)

    inbox = cmo_service.list_recommendation_inbox()

    assert inbox["active_recommendation"]["id"] == "rec-new"
    assert [rec["id"] for rec in inbox["recommendation_history"]] == ["rec-old", "rec-used"]
    assert inbox["recommendation_history"][1]["workflow_state"] == "briefing_created"
    assert inbox["duplicate_count"] == 1


def test_cmo_service_archives_stale_recommendations(cmo_service, mock_env):
    cmo_dir = os.path.join(mock_env, "data", "generated", "cmo-recommendations")
    os.makedirs(cmo_dir, exist_ok=True)
    index_path = os.path.join(cmo_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({
            "recommendations": [
                {
                    "id": "rec-old",
                    "generated_at": "2026-07-05T10:00:00-0300",
                    "status": "draft_recommendation",
                },
                {
                    "id": "rec-new",
                    "generated_at": "2026-07-06T10:00:00-0300",
                    "status": "draft_recommendation",
                },
                {
                    "id": "rec-new",
                    "generated_at": "2026-07-06T10:00:00-0300",
                    "status": "draft_recommendation",
                },
            ]
        }, f)

    result = cmo_service.archive_stale_recommendations(True)

    assert result["status"] == "success"
    assert result["archived_count"] == 2

    inbox = cmo_service.list_recommendation_inbox()
    assert inbox["active_recommendation"]["id"] == "rec-new"
    assert {rec["id"] for rec in inbox["archived_recommendations"]} == {"rec-old"}
    assert inbox["duplicate_count"] == 1


def test_cmo_service_marks_recommendation_as_briefing_created(cmo_service, mock_env):
    setup_cmo_index(mock_env)

    cmo_service.mark_recommendation_briefing_created(
        "rec-active",
        "data/generated/briefings/briefing.md",
        "briefing.md",
    )

    inbox = cmo_service.list_recommendation_inbox()
    assert inbox["active_recommendation"] is None
    assert inbox["recommendation_history"][0]["workflow_state"] == "briefing_created"
    assert inbox["recommendation_history"][0]["briefing_filename"] == "briefing.md"
