import os
import json
import pytest

def test_get_editorial_calendar(calendar_service):
    calendar = calendar_service.get_editorial_calendar()
    
    assert len(calendar) > 0
    # Must not contain "carrossel" which is used_as_asset
    assert not any(item["item_id"] == "carrossel" for item in calendar)

def test_update_item_schedule_rebuilds_markdown(calendar_service):
    folder_id = "2026-01-08-semana-fake2"
    item_id = "post-quarta"
    
    calendar_service.update_item_schedule(folder_id, item_id, {
        "scheduled_for": "2026-02-15",
        "scheduled_time": "14:30"
    })
    
    # Verify publication-log.md was updated
    md_path = os.path.join(calendar_service.history_repo.base_dir, "data", "registry", "publication-log.md")
    assert os.path.exists(md_path)
    
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "Publication Log" in content

def test_add_metrics_snapshot(calendar_service):
    folder_id = "2026-01-01-semana-fake1"
    item_id = "post-segunda"
    
    calendar_service.add_metrics_snapshot(folder_id, item_id, {
        "impressions": 100,
        "reach": 80,
        "reactions": 10,
        "label": "primeiro dia"
    })
    
    history = calendar_service.history_repo.load()
    entry = next(e for e in history if e["id"] == folder_id)
    item = next(i for i in entry["items"] if i["id"] == item_id)
    
    assert "metrics" in item
    assert "latest" in item["metrics"]
    assert item["metrics"]["latest"]["impressions"] == 100
    assert item["metrics"]["latest"]["reach"] == 80
    assert item["metrics"]["latest"]["total_engagements"] == 10
    assert item["metrics"]["latest"]["label"] == "primeiro dia"

def test_generate_snapshot_analysis_success(calendar_service):
    from unittest.mock import MagicMock
    
    folder_id = "2026-01-01-semana-fake1"
    item_id = "post-segunda"
    
    mock_llm = MagicMock()
    mock_llm.generate_content.return_value = "Análise positiva."
    calendar_service.llm_client = mock_llm
    
    snapshot_data = {
        "impressions": 150,
        "reach": 90,
        "reactions": 15
    }
    
    result = calendar_service.generate_snapshot_analysis(folder_id, item_id, snapshot_data)
    
    assert result == "Análise positiva."
    mock_llm.generate_content.assert_called_once()
    system_prompt = mock_llm.generate_content.call_args[0][0]
    user_prompt = mock_llm.generate_content.call_args[0][1]
    
    assert "Você é o Analytics Agent do BrandOS" in system_prompt
    assert "Diferenças calculadas:" in user_prompt

def test_import_linkedin_analytics(calendar_service, tmp_path):
    from unittest.mock import patch
    
    folder_id = "2026-01-01-semana-fake1"
    item_id = "post-segunda"
    
    import pandas as pd
    mock_df = pd.DataFrame({
        "Impressões": [1000],
        "Alcance": [800],
        "Reações": [50]
    })
    
    with patch("pandas.read_excel", return_value=mock_df):
        with patch("shutil.copy2"):
            fake_file = tmp_path / "fake.xlsx"
            fake_file.write_text("fake excel")
            
            result = calendar_service.import_linkedin_analytics(
                folder_id, item_id, str(fake_file), "fake.xlsx"
            )
            
            assert result["impressions"] == 1000
            assert result["reach"] == 800
            assert result["reactions"] == 50
            assert result["total_engagements"] == 50
