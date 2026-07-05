def test_list_history(brandos_service):
    history = brandos_service.list_history()
    assert len(history) == 2
    # Check that nested structure is maintained
    week1 = history[0]
    assert week1["id"] == "2026-01-01-semana-fake1"
    assert len(week1["items"]) == 1
    assert week1["items"][0]["status"] == "published"

def test_get_editorial_calendar(brandos_service):
    calendar = brandos_service.get_editorial_calendar()
    # It returns items as a flat list
    # Expected: item1 (post-segunda), item2 (post-quarta).
    # Asset (carrossel) should be filtered out.
    assert len(calendar) == 2
    assert calendar[0]["item_id"] in ["post-segunda", "post-quarta"]
    assert calendar[1]["item_id"] in ["post-segunda", "post-quarta"]
    
    # Asset 'carrossel' should not be present
    assert not any(i["item_id"] == "carrossel" for i in calendar)

def test_get_dashboard_metrics(brandos_service):
    metrics = brandos_service.get_dashboard_metrics()
    assert metrics["total_weeks"] == 2
    assert metrics["total_items"] == 3  # post-segunda, post-quarta, carrossel
    assert metrics["published_items"] == 1 # post-segunda
    assert metrics["pending_items"] == 1 # post-quarta (draft)
    assert metrics["linked_assets_items"] == 1 # carrossel

def test_list_briefings(brandos_service):
    briefings = brandos_service.list_briefings()
    # Should list both briefings
    assert len(briefings) == 2
    
    b_001 = next(b for b in briefings if b["filename"] == "briefing-001.md")
    b_002 = next(b for b in briefings if b["filename"] == "briefing-002.md")
    
    assert b_001["status"] == "briefing_aprovado"
    assert b_002["status"] == "pendente"

def test_update_item_schedule_rebuilds_markdown(brandos_service):
    """
    Verifica que update_item_schedule() reconstrói o arquivo publication-log.md
    além de salvar no publication-log.json. Isso garante que a chamada
    self._rebuild_markdown_log(history) foi executada.
    """
    import os
    md_path = os.path.join(brandos_service.registry_dir, "publication-log.md")
    
    # Se já existir, remove ou anota o timestamp
    if os.path.exists(md_path):
        os.remove(md_path)
        
    folder_id = "2026-01-01-semana-fake1"
    item_id = "post-segunda"
    schedule_data = {
        "scheduled_for": "2026-02-01",
        "scheduled_time": "10:00",
        "channel": "linkedin"
    }
    
    brandos_service.update_item_schedule(folder_id, item_id, schedule_data)
    
    # O markdown log deve ter sido (re)criado
    assert os.path.exists(md_path)
    
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    assert "Publication Log" in md_content
    # Verifica se a data do log aparece no markdown
    assert "2026-01-01" in md_content

def test_sync_ignores_non_date_folders(tmp_path):
    import os
    import json
    from app.core.brandos_service import BrandOSService
    
    base_dir = str(tmp_path)
    os.makedirs(os.path.join(base_dir, "data", "generated", "briefings"))
    os.makedirs(os.path.join(base_dir, "data", "registry"))
    
    with open(os.path.join(base_dir, "data", "generated", "briefings", "briefing-001.md"), "w", encoding="utf-8") as f:
        f.write("# Briefing Test")
        
    # Inicializa o service com o base_dir que já contém a pasta "briefings"
    service = BrandOSService(base_dir=base_dir)
    
    history = service.list_history()
    
    # Assert que NENHUMA entrada no history se chama "briefings"
    for entry in history:
        assert entry.get("id") != "briefings", f"A pasta 'briefings' não deveria ter sido parseada como semana gerada!"
        assert entry.get("date") != "briefings", f"A pasta 'briefings' não deveria ter sido parseada como data de semana!"


import uuid
import os
import pytest

def setup_test_item(brandos_service, tmp_path, status, extra_attrs=None):
    item_id = str(uuid.uuid4())
    folder_name = "test-folder"
    content_file = f"data/generated/{folder_name}/test-post.md"
    
    file_path = os.path.join(tmp_path, content_file)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("Original content")
        
    item = {
        "id": item_id,
        "title": "Test Post",
        "status": status,
        "content_file": content_file,
        "generated_folder": folder_name,
        "metrics": {"snapshots": [{"test": 1}]},
        "assets": ["asset1"]
    }
    if extra_attrs:
        item.update(extra_attrs)
        
    history = [{
        "date": "2026-07-03",
        "items": [item]
    }]
    brandos_service.history_repo.save(history)
    return item_id, file_path

def test_update_item_content_generated_to_edited(brandos_service, tmp_path):
    item_id, file_path = setup_test_item(brandos_service, tmp_path, "generated")
    
    result = brandos_service.update_item_content(item_id, "New Content", "My source note")
    
    assert result["status"] == "success"
    assert result["new_status"] == "edited"
    assert result["content_version"] == "manual_final"
    assert result["content_source"] == "human_refined"
    
    with open(file_path, "r", encoding="utf-8") as f:
        assert f.read() == "New Content"
        
    history = brandos_service.history_repo.load()
    item = history[0]["items"][0]
    
    assert item["status"] == "edited"
    assert item["content_version"] == "manual_final"
    assert item["content_source"] == "human_refined"
    assert item["edited_by"] == "human"
    assert item["editorial_source"] == "manual_edit"
    assert "last_edited_at" in item
    
    assert len(item["editorial_history"]) == 1
    event = item["editorial_history"][0]
    assert event["event"] == "content_edited"
    assert event["note"] == "My source note"
    assert "backup_file" in event
    
    # Check backup exists
    backup_path = os.path.join(tmp_path, event["backup_file"])
    assert os.path.exists(backup_path)
    with open(backup_path, "r", encoding="utf-8") as f:
        assert f.read() == "Original content"
        
    # Check metrics and assets not modified
    assert item["metrics"]["snapshots"][0]["test"] == 1
    assert item["assets"][0] == "asset1"

def test_update_item_content_preserves_status_for_approved_scheduled(brandos_service, tmp_path):
    for status in ["approved", "scheduled", "publishing_ready", "edited"]:
        item_id, _ = setup_test_item(brandos_service, tmp_path, status)
        brandos_service.update_item_content(item_id, "New Content")
        
        history = brandos_service.history_repo.load()
        item = history[0]["items"][0]
        assert item["status"] == status, f"Status {status} was changed"

def test_update_item_content_blocks_published(brandos_service, tmp_path):
    item_id, _ = setup_test_item(brandos_service, tmp_path, "published")
    with pytest.raises(ValueError, match="já publicados"):
        brandos_service.update_item_content(item_id, "New Content")
    
def test_update_item_content_blocks_assets(brandos_service, tmp_path):
    cases = [
        {"status": "used_as_asset"},
        {"status": "generated", "linked_to_item_id": "other_id"},
        {"status": "generated", "asset_role": "image"}
    ]
    for extra in cases:
        item_id, _ = setup_test_item(brandos_service, tmp_path, extra.get("status"), extra)
        with pytest.raises(ValueError, match="Assets vinculados"):
            brandos_service.update_item_content(item_id, "New Content")

def test_discard_item_success(tmp_path):
    import json
    from app.core.brandos_service import BrandOSService
    from app.core.repositories.history_repository import HistoryRepository
    
    # Setup repo
    registry_dir = tmp_path / "data" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    history_file = registry_dir / "publication-log.json"
    
    generated_dir = tmp_path / "data" / "generated" / "week1"
    generated_dir.mkdir(parents=True, exist_ok=True)
    
    initial_history = [
        {
            "id": "week1",
            "date": "2024-01-01",
            "items": [
                {
                    "id": "post1",
                    "status": "scheduled",
                    "scheduled_for": "2024-01-02",
                    "scheduled_time": "12:00",
                    "priority": "alta"
                }
            ]
        }
    ]
    history_file.write_text(json.dumps(initial_history, ensure_ascii=False, indent=2), encoding='utf-8')
    
    service = BrandOSService(base_dir=str(tmp_path))
    
    # Discard item
    result = service.discard_item("post1", "Motivo de teste", True)
    
    assert result["status"] == "success"
    
    # Reload and check history
    repo = HistoryRepository(str(tmp_path))
    history = repo.load()
    
    item = history[0]["items"][0]
    assert item["status"] == "discarded"
    assert "discard_history" in item
    assert len(item["discard_history"]) == 1
    assert item["discard_history"][0]["reason"] == "Motivo de teste"
    
    # Verify schedule data is cleared
    assert "scheduled_for" not in item
    assert "scheduled_time" not in item
    assert "scheduled_date" not in item
    assert "priority" not in item
