import os
import json
import pytest
from app.core.brandos_service import BrandOSService
from app.core.services.asset_service import AssetService
from app.core.repositories.history_repository import HistoryRepository

def setup_mock_env(base_dir):
    # Create directories
    os.makedirs(os.path.join(base_dir, "data", "generated"))
    os.makedirs(os.path.join(base_dir, "data", "knowledge"))
    os.makedirs(os.path.join(base_dir, "data", "registry"))
    os.makedirs(os.path.join(base_dir, "data", "assets"))
    
    # 1. Fake Registry (publication-log.json)
    registry_path = os.path.join(base_dir, "data", "registry", "publication-log.json")
    registry_data = [
        {
            "id": "2026-01-01-semana-fake1",
            "date": "2026-01-01",
            "project": "Fake Project 1",
            "theme": "Semana Fake 1",
            "status": "published",
            "items": [
                {
                    "id": "post-segunda",
                    "title": "Post segunda",
                    "type": "linkedin_post",
                    "file": "03-post-segunda.md",
                    "status": "published",
                    "published_at": "2026-01-02",
                    "scheduled_for": "2026-01-02",
                    "channel": "linkedin"
                }
            ]
        },
        {
            "id": "2026-01-08-semana-fake2",
            "date": "2026-01-08",
            "project": "Fake Project 2",
            "theme": "Semana Fake 2",
            "status": "in_progress",
            "items": [
                {
                    "id": "post-quarta",
                    "title": "Post quarta",
                    "type": "linkedin_post",
                    "file": "04-post-quarta.md",
                    "status": "draft",
                    "scheduled_for": "2026-01-10",
                    "channel": "linkedin"
                },
                {
                    "id": "carrossel",
                    "title": "Carrossel PDF",
                    "type": "carousel",
                    "file": "06-carrossel.md",
                    "status": "used_as_asset",
                    "linked_to_item_id": "post-quarta"
                }
            ]
        }
    ]
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry_data, f, ensure_ascii=False, indent=2)
        
    # 3. Create dummy markdown files for the generated folders
    week1_dir = os.path.join(base_dir, "data", "generated", "2026-01-01-semana-fake1")
    os.makedirs(week1_dir)
    with open(os.path.join(week1_dir, "03-post-segunda.md"), "w", encoding="utf-8") as f:
        f.write("Conteudo Post 1")
        
    week2_dir = os.path.join(base_dir, "data", "generated", "2026-01-08-semana-fake2")
    os.makedirs(week2_dir)
    with open(os.path.join(week2_dir, "04-post-quarta.md"), "w", encoding="utf-8") as f:
        f.write("Conteudo Post 2")
        
    # 4. Fake Briefings
    briefings_dir = os.path.join(base_dir, "data", "generated", "briefings")
    os.makedirs(briefings_dir)
    with open(os.path.join(briefings_dir, "briefing-001.md"), "w", encoding="utf-8") as f:
        f.write("Data de criação: 2026-07-03\nFonte: Teste\nStatus: briefing_aprovado\n\n# Briefing 001")
    with open(os.path.join(briefings_dir, "briefing-002.md"), "w", encoding="utf-8") as f:
        f.write("Data de criação: 2026-07-03\nFonte: Teste\nStatus: pendente\n\n# Briefing 002")

@pytest.fixture
def mock_env(tmp_path):
    base_dir = str(tmp_path)
    setup_mock_env(base_dir)
    return base_dir

@pytest.fixture
def brandos_service(mock_env):
    return BrandOSService(base_dir=mock_env)

@pytest.fixture
def asset_service(mock_env):
    history_repo = HistoryRepository(base_dir=mock_env)
    assets_dir = os.path.join(mock_env, "data", "assets")
    return AssetService(assets_dir=assets_dir, history_repo=history_repo)
