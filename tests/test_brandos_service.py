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
