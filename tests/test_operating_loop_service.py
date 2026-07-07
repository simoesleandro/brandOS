import json
import os
from datetime import datetime, timedelta


def test_operating_loop_prioritizes_due_publication(operating_loop_service):
    history = operating_loop_service.history_repo.load()
    item = history[1]["items"][0]
    item["status"] = "scheduled"
    item["scheduled_date"] = "2020-01-01"
    operating_loop_service.history_repo.save(history)

    result = operating_loop_service.get_today_operating_loop()

    assert result["next_action"] == "publish_due"
    assert result["primary_item"]["id"] == "post-quarta"
    assert result["due_publications"]


def test_operating_loop_prioritizes_due_metrics_when_no_publication_due(operating_loop_service):
    history = operating_loop_service.history_repo.load()
    item = history[0]["items"][0]
    item["status"] = "published"
    item["post_publish_tracking_status"] = "waiting_24h_metrics"
    item["metrics_due_24h_at"] = "2020-01-02T10:00:00"
    history[1]["items"][0]["status"] = "approved"
    operating_loop_service.history_repo.save(history)

    result = operating_loop_service.get_today_operating_loop()

    assert result["next_action"] == "capture_metrics"
    assert result["primary_item"]["id"] == "post-segunda"
    assert result["due_metrics"]


def test_operating_loop_ignores_metrics_not_due_yet(operating_loop_service):
    future = (datetime.now() + timedelta(days=2)).isoformat()
    history = operating_loop_service.history_repo.load()
    item = history[0]["items"][0]
    item["status"] = "published"
    item["post_publish_tracking_status"] = "waiting_24h_metrics"
    item["metrics_due_24h_at"] = future
    history[1]["items"][0]["status"] = "approved"
    operating_loop_service.history_repo.save(history)

    result = operating_loop_service.get_today_operating_loop()

    assert result["next_action"] != "capture_metrics"
    assert result["due_metrics"] == []


def test_operating_loop_ignores_completed_tracking(operating_loop_service):
    history = operating_loop_service.history_repo.load()
    item = history[0]["items"][0]
    item["status"] = "published"
    item["post_publish_tracking_status"] = "completed"
    item["metrics_due_24h_at"] = "2020-01-02T10:00:00"
    history[1]["items"][0]["status"] = "approved"
    operating_loop_service.history_repo.save(history)

    result = operating_loop_service.get_today_operating_loop()

    assert result["next_action"] != "capture_metrics"
    assert result["due_metrics"] == []


def test_operating_loop_prioritizes_review_generated(operating_loop_service):
    result = operating_loop_service.get_today_operating_loop()

    assert result["next_action"] == "review_generated"
    assert result["primary_item"]["id"] == "post-quarta"


def test_operating_loop_finds_approved_briefing_waiting_generation(operating_loop_service):
    history = operating_loop_service.history_repo.load()
    history[1]["items"][0]["status"] = "approved"
    operating_loop_service.history_repo.save(history)

    result = operating_loop_service.get_today_operating_loop()

    assert result["next_action"] == "approve_briefing"
    assert result["approved_briefings"][0]["filename"] == "briefing-001.md"


def test_operating_loop_finds_cmo_recommendation_when_no_briefing_or_posts(operating_loop_service, mock_env):
    history = operating_loop_service.history_repo.load()
    for entry in history:
        for item in entry.get("items", []):
            if item.get("status") != "used_as_asset":
                item["status"] = "published"
                item["post_publish_tracking_status"] = "completed"
    operating_loop_service.history_repo.save(history)

    for briefing in ["briefing-001.md", "briefing-002.md"]:
        path = os.path.join(mock_env, "data", "generated", "briefings", briefing)
        with open(path, "w", encoding="utf-8") as f:
            f.write("Status: generated\nGenerated folder: done\n")

    cmo_dir = os.path.join(mock_env, "data", "generated", "cmo-recommendations")
    os.makedirs(cmo_dir, exist_ok=True)
    with open(os.path.join(cmo_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump({
            "recommendations": [
                {"id": "rec-001", "generated_at": "2026-07-07T10:00:00-0300", "status": "active"}
            ]
        }, f)

    result = operating_loop_service.get_today_operating_loop()

    assert result["next_action"] == "create_next_briefing"
    assert result["primary_item"]["id"] == "rec-001"
