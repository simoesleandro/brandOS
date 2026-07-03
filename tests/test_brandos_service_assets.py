import os
import json
import pytest

def test_init_item_assets_success(asset_service):
    folder_id = "2026-01-01-semana-fake1"
    item_id = "post-segunda"
    
    manifest_path = asset_service.init_item_assets(folder_id, item_id)
    
    # Verifies file exists
    assert os.path.exists(manifest_path)
    
    # Verifies the subfolders are created
    asset_folder = os.path.dirname(manifest_path)
    assert os.path.exists(os.path.join(asset_folder, "images"))
    assert os.path.exists(os.path.join(asset_folder, "pdf"))
    
    # Verifies publication-log.json was updated
    history = asset_service.history_repo.load()
    entry = next(e for e in history if e["id"] == folder_id)
    item = next(i for i in entry["items"] if i["id"] == item_id)
    assert "assets" in item
    assert "manifest" in item["assets"]

def test_init_item_assets_error(asset_service):
    with pytest.raises(ValueError, match="Peça não encontrada"):
        asset_service.init_item_assets("2026-01-01-semana-fake1", "item-nao-existe")

def test_upload_item_asset_success(asset_service):
    folder_id = "2026-01-01-semana-fake1"
    item_id = "post-segunda"
    asset_service.init_item_assets(folder_id, item_id)
    
    file_content = b"fake image content"
    file_name = "test_image.jpg"
    
    result_path = asset_service.upload_item_asset(
        folder_id=folder_id,
        item_id=item_id,
        file_name=file_name,
        file_content=file_content,
        asset_category="images"
    )
    
    assert os.path.exists(result_path)
    
    manifest_path = os.path.join(asset_service.assets_dir, f"{folder_id}-{item_id}", "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    assert any(img["file_name"] == "test_image.jpg" for img in manifest["files"]["images"])

def test_upload_item_asset_error(asset_service):
    folder_id = "2026-01-08-semana-fake2"
    item_id = "post-quarta"
    # Not calling init_item_assets first
    
    with pytest.raises(ValueError, match="Pasta de assets não inicializada"):
        asset_service.upload_item_asset(
            folder_id=folder_id,
            item_id=item_id,
            file_name="test.jpg",
            file_content=b"123",
            asset_category="images"
        )

def test_add_item_asset_prompt_success(asset_service):
    folder_id = "2026-01-01-semana-fake1"
    item_id = "post-segunda"
    asset_service.init_item_assets(folder_id, item_id)
    
    asset_service.add_item_asset_prompt(folder_id, item_id, "Draw a cool cat")
    
    manifest_path = os.path.join(asset_service.assets_dir, f"{folder_id}-{item_id}", "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    prompts = manifest["files"].get("prompts", [])
    assert len(prompts) == 1
    assert prompts[0]["content"] == "Draw a cool cat"
    assert prompts[0]["source"] == "manual"

def test_get_recommended_prompts(asset_service):
    folder_id = "2026-01-01-semana-fake1"
    
    # Create fake prompt file in generated dir
    gen_dir = os.path.join(asset_service.history_repo.base_dir, "data", "generated", folder_id)
    prompt_file = os.path.join(gen_dir, "07-prompts.md")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Some recommended prompt here")
        
    res = asset_service.get_recommended_prompts(folder_id)
    assert res is not None
    assert res["filename"] == "07-prompts.md"
    assert res["content"] == "Some recommended prompt here"

def test_import_recommended_prompt(asset_service):
    folder_id = "2026-01-01-semana-fake1"
    item_id = "post-segunda"
    asset_service.init_item_assets(folder_id, item_id)
    
    # Create fake prompt file
    gen_dir = os.path.join(asset_service.history_repo.base_dir, "data", "generated", folder_id)
    prompt_file = os.path.join(gen_dir, "07-prompts.md")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Generated prompt")
        
    asset_service.import_recommended_prompt(folder_id, item_id, "07-prompts.md")
    
    manifest_path = os.path.join(asset_service.assets_dir, f"{folder_id}-{item_id}", "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    prompts = manifest["files"].get("prompts", [])
    assert len(prompts) == 1
    assert prompts[0]["content"] == "Generated prompt"
    assert prompts[0]["source"] == "generated"

def test_delete_item_asset(asset_service):
    folder_id = "2026-01-01-semana-fake1"
    item_id = "post-segunda"
    asset_service.init_item_assets(folder_id, item_id)
    
    asset_service.upload_item_asset(
        folder_id=folder_id,
        item_id=item_id,
        file_name="todelete.pdf",
        file_content=b"pdf",
        asset_category="pdf"
    )
    
    manifest_path = os.path.join(asset_service.assets_dir, f"{folder_id}-{item_id}", "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert len(manifest["files"]["pdf"]) == 1
    
    # Delete it
    asset_service.delete_item_asset(folder_id, item_id, "pdf", "todelete.pdf")
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert len(manifest["files"]["pdf"]) == 0
    
    asset_file_path = os.path.join(asset_service.assets_dir, f"{folder_id}-{item_id}", "pdf", "todelete.pdf")
    assert not os.path.exists(asset_file_path)

def test_delete_item_prompt(asset_service):
    folder_id = "2026-01-01-semana-fake1"
    item_id = "post-segunda"
    asset_service.init_item_assets(folder_id, item_id)
    
    asset_service.add_item_asset_prompt(folder_id, item_id, "Draw a dog")
    
    manifest_path = os.path.join(asset_service.assets_dir, f"{folder_id}-{item_id}", "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    prompt_id = manifest["files"]["prompts"][0]["id"]
    
    # Delete by id
    asset_service.delete_item_prompt(folder_id, item_id, prompt_id=prompt_id)
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert len(manifest["files"].get("prompts", [])) == 0
