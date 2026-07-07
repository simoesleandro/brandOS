import os
import json
import pytest
from app.core.repositories.history_repository import HistoryRepository

def test_history_repo_load_empty(tmp_path):
    repo = HistoryRepository(str(tmp_path))
    assert repo.load() == []

def test_history_repo_load_success(tmp_path):
    base_dir = str(tmp_path)
    registry_dir = os.path.join(base_dir, "data", "registry")
    os.makedirs(registry_dir, exist_ok=True)
    json_path = os.path.join(registry_dir, "publication-log.json")
    
    test_data = [{"id": "test", "status": "published"}]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(test_data, f)
        
    repo = HistoryRepository(base_dir)
    loaded = repo.load()
    assert len(loaded) == 1
    assert loaded[0]["id"] == "test"

def test_history_repo_load_invalid_json_raises(tmp_path):
    base_dir = str(tmp_path)
    registry_dir = os.path.join(base_dir, "data", "registry")
    os.makedirs(registry_dir, exist_ok=True)
    json_path = os.path.join(registry_dir, "publication-log.json")

    with open(json_path, "w", encoding="utf-8") as f:
        f.write("{invalid json")

    repo = HistoryRepository(base_dir)

    with pytest.raises(ValueError, match="Invalid publication-log.json"):
        repo.load()

def test_history_repo_iter_items_and_find_item(tmp_path):
    base_dir = str(tmp_path)
    repo = HistoryRepository(base_dir)

    history = [
        {
            "id": "week-1",
            "date": "2026-07-06",
            "items": [
                {"id": "legacy-id", "title": "Legacy"},
                {"id": "internal-id", "item_id": "public-id", "title": "Public"},
            ],
        }
    ]
    repo.save(history)

    pairs = list(repo.iter_items())
    assert len(pairs) == 2
    assert pairs[0][0]["id"] == "week-1"
    assert pairs[0][1]["id"] == "legacy-id"

    entry, item = repo.find_item("public-id")
    assert entry["id"] == "week-1"
    assert item["title"] == "Public"

    entry, item = repo.find_item("legacy-id")
    assert entry["id"] == "week-1"
    assert item["title"] == "Legacy"

def test_history_repo_preview_invalid_root_items(tmp_path):
    base_dir = str(tmp_path)
    repo = HistoryRepository(base_dir)

    history = [
        {"id": "week-1", "date": "2026-07-06", "items": []},
        {"item_id": "loose-test", "title": "Loose Test", "status": "generated"},
    ]

    suspects = repo.preview_invalid_items(history)

    assert len(suspects) == 1
    assert suspects[0]["identifier"] == "loose-test"
    assert suspects[0]["reason"] == "Loose item at registry root"

def test_history_repo_save(tmp_path):
    base_dir = str(tmp_path)
    repo = HistoryRepository(base_dir)
    
    test_data = [{"id": "test_save", "status": "draft", "date": "2026-07-03", "project": "Test"}]
    repo.save(test_data)
    
    json_path = os.path.join(base_dir, "data", "registry", "publication-log.json")
    md_path = os.path.join(base_dir, "data", "registry", "publication-log.md")
    
    assert os.path.exists(json_path)
    assert os.path.exists(md_path)
    
    with open(json_path, "r", encoding="utf-8") as f:
        saved_json = json.load(f)
    assert saved_json[0]["id"] == "test_save"
    
    with open(md_path, "r", encoding="utf-8") as f:
        saved_md = f.read()
    assert "2026-07-03" in saved_md
    assert "Test" in saved_md
