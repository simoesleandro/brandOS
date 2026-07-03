import os
import re
import json
from datetime import datetime
from app.core.repositories.history_repository import HistoryRepository

class AssetService:
    def __init__(self, assets_dir: str, history_repo: HistoryRepository):
        self.assets_dir = assets_dir
        self.history_repo = history_repo

    def init_item_assets(self, folder_id: str, item_id: str):
        history = self.history_repo.load()
        entry = next((e for e in history if e.get("id") == folder_id or e.get("date") == folder_id[:10]), None)
        if not entry:
            raise ValueError("Geração não encontrada.")
            
        item = next((i for i in entry.get("items", []) if i.get("id") == item_id), None)
        if not item:
            raise ValueError("Peça não encontrada.")
            
        asset_folder_name = f"{folder_id}-{item_id}"
        asset_folder_path = os.path.join(self.assets_dir, asset_folder_name)
        manifest_path = os.path.join(asset_folder_path, "manifest.json")
        
        # Cria a pasta de assets e subpastas
        os.makedirs(asset_folder_path, exist_ok=True)
        for sub in ["images", "slides", "pdf", "video", "prompts", "source"]:
            os.makedirs(os.path.join(asset_folder_path, sub), exist_ok=True)
            
        # Cria ou preserva manifest
        if not os.path.exists(manifest_path):
            manifest = {
                "generation_id": folder_id,
                "item_id": item_id,
                "project": entry.get("project"),
                "title": item.get("title"),
                "asset_type": item.get("type"),
                "status": item.get("status"),
                "files": {
                    "images": [],
                    "slides": [],
                    "pdf": [],
                    "video": [],
                    "prompts": [],
                    "source": []
                },
                "published_at": None,
                "notes": ""
            }
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
                
        # Atualiza o publication-log.json
        item["assets"] = {
            "asset_folder": f"data/assets/{asset_folder_name}",
            "manifest": f"data/assets/{asset_folder_name}/manifest.json"
        }
        self.history_repo.save(history)
        return manifest_path

    def upload_item_asset(self, folder_id: str, item_id: str, file_name: str, file_content: bytes, asset_category: str, asset_role: str = ""):
        # Sanitizar nome
        clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '-', file_name).lower()
        clean_name = re.sub(r'-+', '-', clean_name).strip('-')
        
        import os
        base, ext = os.path.splitext(clean_name)
        
        # Infer role se vazio
        if not asset_role:
            if re.match(r'^slide[-_]?\d+$', base):
                asset_role = base.replace('-', '_')
            elif base in ['cover', 'capa']:
                asset_role = 'cover'
            elif base == 'final':
                asset_role = 'final'
        
        ext_lower = ext.lower()
        if ext_lower == '.pdf':
            asset_category = 'pdf'
        elif ext_lower in ['.png', '.jpg', '.jpeg', '.webp']:
            asset_category = 'images'
        elif ext_lower in ['.mp4', '.mov', '.webm']:
            asset_category = 'video'
        elif ext_lower in ['.html', '.css', '.js', '.md', '.zip']:
            asset_category = 'source'
            
        asset_folder_name = f"{folder_id}-{item_id}"
        asset_folder_path = os.path.join(self.assets_dir, asset_folder_name)
        manifest_path = os.path.join(asset_folder_path, "manifest.json")
        
        if not os.path.exists(manifest_path):
            raise ValueError("Pasta de assets não inicializada.")
            
        category_path = os.path.join(asset_folder_path, asset_category)
        os.makedirs(category_path, exist_ok=True)
        
        # Evitar sobrescrever
        base, ext = os.path.splitext(clean_name)
        final_name = clean_name
        counter = 2
        while os.path.exists(os.path.join(category_path, final_name)):
            final_name = f"{base}-{counter}{ext}"
            counter += 1
            
        final_path = os.path.join(category_path, final_name)
        
        # Escrever arquivo
        with open(final_path, "wb") as f:
            f.write(file_content)
            
        # Atualizar manifest
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        if asset_category not in manifest["files"]:
            manifest["files"][asset_category] = []
            
        # O PDF antigo pedia null, mas na real é melhor usar array para manter histórico de revisões
        # Convertemos para lista se ainda for dict/null (para backwards compatibility do design que o usuário mandou)
        if not isinstance(manifest["files"][asset_category], list):
            manifest["files"][asset_category] = []
            
        manifest["files"][asset_category].append({
            "file_name": final_name,
            "path": f"data/assets/{asset_folder_name}/{asset_category}/{final_name}",
            "asset_role": asset_role,
            "uploaded_at": datetime.now().isoformat()
        })
        
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            
        return final_path

    def add_item_asset_prompt(self, folder_id: str, item_id: str, prompt_text: str):
        asset_folder_name = f"{folder_id}-{item_id}"
        asset_folder_path = os.path.join(self.assets_dir, asset_folder_name)
        manifest_path = os.path.join(asset_folder_path, "manifest.json")
        
        if not os.path.exists(manifest_path):
            raise ValueError("Pasta de assets não inicializada.")
            
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        if "prompts" not in manifest["files"] or not isinstance(manifest["files"]["prompts"], list):
            manifest["files"]["prompts"] = []
            
        # Deduplication check
        for p in manifest["files"]["prompts"]:
            if isinstance(p, dict) and p.get("content") == prompt_text:
                return # Already exists
                
        import uuid
        manifest["files"]["prompts"].append({
            "id": str(uuid.uuid4()),
            "title": "Prompt manual",
            "content": prompt_text,
            "source": "manual",
            "created_at": datetime.now().isoformat(),
            "status": "saved"
        })
        
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            
    def get_recommended_prompts(self, folder_id: str):
        import glob
        gen_dir = os.path.join(self.history_repo.base_dir, "data", "generated", folder_id)
        if not os.path.exists(gen_dir):
            return None
            
        # Look for files matching *prompt* or *visual* or *imagem*
        files = os.listdir(gen_dir)
        for fname in files:
            lower_f = fname.lower()
            if fname.endswith('.md') and ('prompt' in lower_f or 'visual' in lower_f or 'imagem' in lower_f or 'midjourney' in lower_f):
                with open(os.path.join(gen_dir, fname), 'r', encoding='utf-8') as f:
                    content = f.read()
                return {
                    "filename": fname,
                    "content": content
                }
        return None
        
    def import_recommended_prompt(self, folder_id: str, item_id: str, filename: str):
        asset_folder_name = f"{folder_id}-{item_id}"
        asset_folder_path = os.path.join(self.assets_dir, asset_folder_name)
        manifest_path = os.path.join(asset_folder_path, "manifest.json")
        
        gen_dir = os.path.join(self.history_repo.base_dir, "data", "generated", folder_id)
        source_path = os.path.join(gen_dir, filename)
        
        if not os.path.exists(source_path):
            raise ValueError("Arquivo de prompt não encontrado.")
            
        with open(source_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if not os.path.exists(manifest_path):
            raise ValueError("Pasta de assets não inicializada.")
            
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        if "prompts" not in manifest["files"] or not isinstance(manifest["files"]["prompts"], list):
            manifest["files"]["prompts"] = []
            
        # Deduplication
        for p in manifest["files"]["prompts"]:
            if isinstance(p, dict) and (p.get("source_file") == filename or p.get("content") == content):
                return
                
        import uuid
        manifest["files"]["prompts"].append({
            "id": str(uuid.uuid4()),
            "title": "Prompt visual da geração",
            "content": content,
            "source": "generated",
            "source_file": filename,
            "created_at": datetime.now().isoformat(),
            "status": "saved"
        })
        
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def delete_item_asset(self, folder_id: str, item_id: str, category: str, filename: str):
        from pathlib import Path
        
        valid_categories = {"images", "slides", "pdf", "video", "source", "prompts"}
        if category not in valid_categories:
            raise ValueError(f"Categoria inválida: {category}")
            
        asset_folder_name = f"{folder_id}-{item_id}"
        assets_base = Path(self.assets_dir).resolve()
        target_path = (assets_base / asset_folder_name / category / filename).resolve()
        
        # Path traversal protection
        if not str(target_path).startswith(str(assets_base)):
            raise ValueError("Acesso negado: path traversal detectado.")
            
        # Remover do disco
        if target_path.exists() and target_path.is_file():
            target_path.unlink()
            print(f"[{folder_id}/{item_id}] Arquivo removido: {target_path}")
            
        # Remover do manifest
        manifest_path = os.path.join(self.assets_dir, asset_folder_name, "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                
            if category in manifest.get("files", {}) and isinstance(manifest["files"][category], list):
                original_len = len(manifest["files"][category])
                manifest["files"][category] = [
                    item for item in manifest["files"][category] 
                    if isinstance(item, dict) and item.get("file_name") != filename
                ]
                
                if len(manifest["files"][category]) < original_len:
                    with open(manifest_path, "w", encoding="utf-8") as f:
                        json.dump(manifest, f, indent=2, ensure_ascii=False)
                    print(f"[{folder_id}/{item_id}] Referência de '{filename}' removida do manifest na categoria '{category}'.")

    def delete_item_prompt(self, folder_id: str, item_id: str, prompt_id: str = None, prompt_index: int = None):
        asset_folder_name = f"{folder_id}-{item_id}"
        manifest_path = os.path.join(self.assets_dir, asset_folder_name, "manifest.json")
        
        if not os.path.exists(manifest_path):
            return
            
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        if "prompts" in manifest.get("files", {}) and isinstance(manifest["files"]["prompts"], list):
            prompts = manifest["files"]["prompts"]
            original_len = len(prompts)
            
            if prompt_id:
                manifest["files"]["prompts"] = [p for p in prompts if isinstance(p, dict) and p.get("id") != prompt_id]
            elif prompt_index is not None and 0 <= prompt_index < len(prompts):
                manifest["files"]["prompts"].pop(prompt_index)
                
            if len(manifest["files"]["prompts"]) < original_len:
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)
                print(f"[{folder_id}/{item_id}] Prompt removido do manifest.")
