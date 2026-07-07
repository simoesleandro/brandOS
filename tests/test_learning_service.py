import json
import os


def test_learning_service_returns_latest_strategic_memory(learning_service, mock_env):
    memory_dir = os.path.join(mock_env, "data", "generated", "strategic-memory")
    os.makedirs(memory_dir, exist_ok=True)

    old_path = os.path.join(memory_dir, "old.md")
    latest_path = os.path.join(memory_dir, "latest.md")
    with open(old_path, "w", encoding="utf-8") as f:
        f.write("memoria antiga")
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write("memoria recente")

    with open(os.path.join(memory_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump({
            "memories": [
                {"id": "old", "file": "data/generated/strategic-memory/old.md", "generated_at": "2026-07-05T10:00:00-0300"},
                {"id": "latest", "file": "data/generated/strategic-memory/latest.md", "generated_at": "2026-07-06T10:00:00-0300"},
            ]
        }, f)

    latest = learning_service.get_latest_strategic_memory()

    assert latest["id"] == "latest"
    assert latest["content"] == "memoria recente"


def test_learning_service_rejects_invalid_strategic_memory_window(learning_service):
    result = learning_service.generate_strategic_memory(confirm=True, window_days=3)

    assert result["status"] == "error"
    assert "entre 7 e 180" in result["message"]
