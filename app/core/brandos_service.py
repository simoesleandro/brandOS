import os
import re
import json
from datetime import datetime
from app.workflows.weekly_workflow import run_weekly_workflow

class BrandOSService:
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.registry_dir = os.path.join(self.base_dir, "data", "registry")
        self.knowledge_dir = os.path.join(self.base_dir, "data", "knowledge")
        self.inbox_dir = os.path.join(self.base_dir, "data", "inbox")
        self.generated_dir = os.path.join(self.base_dir, "data", "generated")
        self.assets_dir = os.path.join(self.base_dir, "data", "assets")
        os.makedirs(self.assets_dir, exist_ok=True)
        self._sync_generated_to_history()

    def _sync_generated_to_history(self):
        """Varre as pastas geradas e garante que existam no publication-log.json com a nova estrutura de itens."""
        if not os.path.exists(self.generated_dir):
            return
            
        history = self.list_history()
        known_dates = [entry.get("date") for entry in history]
        
        json_path = os.path.join(self.registry_dir, "publication-log.json")
        updated = False
        
        for folder in sorted(os.listdir(self.generated_dir)):
            folder_path = os.path.join(self.generated_dir, folder)
            if not os.path.isdir(folder_path):
                continue
                
            date_prefix = folder[:10]
            if date_prefix not in known_dates:
                # Criar nova entrada
                files = os.listdir(folder_path)
                
                # Heurística simples para extrair o tema e projeto do nome da pasta
                # A pasta padrão é: YYYY-MM-DD-semana-projeto
                parts = folder.split("-")
                project_name = "-".join(parts[4:]) if len(parts) > 4 else "Desconhecido"
                
                entry = {
                    "id": folder,
                    "date": date_prefix,
                    "project": project_name.capitalize(),
                    "theme": "Semana " + date_prefix,
                    "status": "generated",
                    "items": []
                }
                
                # Mapear arquivos encontrados para itens
                for f in sorted(files):
                    if not f.endswith(".md"): continue
                    item_type = "document"
                    if "post" in f: item_type = "linkedin_post"
                    elif "carrossel" in f: item_type = "carousel"
                    elif "comentario" in f: item_type = "comment"
                    elif "instrucoes" in f: item_type = "instructions"
                    
                    entry["items"].append({
                        "id": f.replace(".md", "").split("-", 1)[-1] if "-" in f else f.replace(".md", ""),
                        "title": f.replace(".md", "").replace("-", " ").capitalize(),
                        "type": item_type,
                        "file": f,
                        "status": "draft" if item_type in ["linkedin_post", "carousel"] else "generated",
                        "metrics": {}
                    })
                
                history.append(entry)
                known_dates.append(date_prefix)
                updated = True
                
        if updated:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            self._rebuild_markdown_log(history)


    def _rebuild_markdown_log(self, history):
        md_path = os.path.join(self.registry_dir, "publication-log.md")
        md_content = "# Publication Log\n\n| Data | Projeto | Status Geral |\n|---|---|---|\n"
        for entry in history:
            md_content += f"| {entry.get('date', '')} | {entry.get('project', '')} | {entry.get('status', '')} |\n"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)


    def _recalculate_week_status(self, entry):
        """
        Calcula o status da semana com base nos seus itens.
        Se todos os itens principais (posts, carrossel) estiverem published/skipped, a semana é published.
        Se houver algo draft/ready, é partially_published ou in_progress.
        """
        main_types = ["linkedin_post", "carousel"]
        main_items = [i for i in entry.get("items", []) if i.get("type") in main_types]
        
        if not main_items:
            return "generated"
            
        all_done = all(i.get("status") in ["published", "skipped"] for i in main_items)
        any_done = any(i.get("status") in ["published", "skipped"] for i in main_items)
        
        if all_done:
            return "published"
        elif any_done:
            return "partially_published"
        else:
            return "in_progress"

    def run_weekly_generation(self, mode: str, project: str = "", briefing: str = ""):
        briefing_path = os.path.join(self.inbox_dir, "briefing-da-semana.md")
        os.makedirs(self.inbox_dir, exist_ok=True)

        if mode == "manual":
            content = f"# Projeto em foco desta semana\n{project}\n\n# Briefing\n{briefing}"
            with open(briefing_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            if os.path.exists(briefing_path):
                with open(briefing_path, "w", encoding="utf-8") as f:
                    f.write("")

        run_weekly_workflow(base_dir=self.base_dir)
        self._sync_generated_to_history()
        return True

    def list_history(self):
        json_path = os.path.join(self.registry_dir, "publication-log.json")
        if not os.path.exists(json_path):
            return []
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def update_item_status(self, folder_id: str, item_id: str, new_status: str):
        """Atualiza o status de um item específico."""
        history = self.list_history()
        date_prefix = folder_id[:10]
        json_path = os.path.join(self.registry_dir, "publication-log.json")
        
        updated = False
        for entry in history:
            if entry.get("date") == date_prefix or entry.get("id") == folder_id:
                for item in entry.get("items", []):
                    if item.get("id") == item_id:
                        item["status"] = new_status
                        if new_status == "published":
                            item["published_at"] = datetime.now().isoformat()
                        updated = True
                        break
                
                if updated:
                    entry["status"] = self._recalculate_week_status(entry)
                    break
                
        if updated:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            self._rebuild_markdown_log(history)

    def get_dashboard_metrics(self):
        history = self.list_history()
        
        total_weeks = len(history)
        total_items = 0
        ready_items = 0
        published_items = 0
        pending_items = 0
        active_projects = set()
        recent_activity = []
        queue = []
        
        for entry in history:
            active_projects.add(entry.get("project"))
            for item in entry.get("items", []):
                total_items += 1
                status = item.get("status")
                
                # Fila e métricas principais (apenas posts e carrosseis)
                if item.get("type") in ["linkedin_post", "carousel"]:
                    # Heuristica de folder_id
                    folder_id = entry.get("id") or f"{entry.get('date')}-semana-brandos"
                    
                    if status == "ready_to_publish":
                        ready_items += 1
                        queue.append({"project": entry.get("project"), "title": item.get("title"), "status": status, "folder_id": folder_id, "item_id": item.get("id")})
                    elif status == "published":
                        published_items += 1
                        recent_activity.append({"action": f"{item.get('title')} publicado", "project": entry.get("project"), "time": item.get("published_at")})
                    elif status in ["draft", "generated", "needs_revision"]:
                        pending_items += 1
                        queue.append({"project": entry.get("project"), "title": item.get("title"), "status": status, "folder_id": folder_id, "item_id": item.get("id")})
                        
        # Organiza a fila para mostrar ready primeiro
        queue.sort(key=lambda x: 0 if x["status"] == "ready_to_publish" else 1)
        
        return {
            "total_weeks": total_weeks,
            "total_items": total_items,
            "ready_items": ready_items,
            "published_items": published_items,
            "pending_items": pending_items,
            "total_projects": len(active_projects),
            "queue": queue[:5], # Mostrar as 5 proximas
            "recent_activity": sorted(recent_activity, key=lambda x: x.get("time") or "", reverse=True)[:5]
        }

    def list_generated_weeks(self):
        """Retorna as semanas do json, que estão sincronizadas com as pastas."""
        return self.list_history()

    def get_generation_details(self, folder_id: str):
        history = self.list_history()
        date_prefix = folder_id[:10]
        
        entry = next((e for e in history if e.get("date") == date_prefix or e.get("id") == folder_id), None)
        if not entry:
            return None
            
        folder_path = os.path.join(self.generated_dir, folder_id)
        
        # Injeta o conteúdo dos arquivos no item temporariamente para a view
        for item in entry.get("items", []):
            file_path = os.path.join(folder_path, item.get("file", ""))
            try:
                item["file_exists"] = os.path.exists(file_path)
                item["content_available"] = item["file_exists"]
                
                if item["file_exists"]:
                    with open(file_path, "r", encoding="utf-8") as f:
                        item["content"] = f.read()
                else:
                    item["content"] = "Arquivo não encontrado no disco."
                    if item.get("status") not in ["skipped", "missing"]:
                        item["status"] = "missing"
            except Exception as e:
                item["content"] = f"Erro ao ler arquivo: {str(e)}"
                item["file_exists"] = False
                item["content_available"] = False
                
            if item.get("assets") and item["assets"].get("manifest"):
                manifest_path = os.path.join(self.base_dir, item["assets"]["manifest"])
                try:
                    if os.path.exists(manifest_path):
                        with open(manifest_path, "r", encoding="utf-8") as fm:
                            item["manifest"] = json.load(fm)
                except Exception as me:
                    print(f"Erro ao carregar manifest: {me}")
                
        return entry

    def get_official_links(self):
        path = os.path.join(self.knowledge_dir, "links-oficiais.md")
        if not os.path.exists(path): return ""
        with open(path, "r", encoding="utf-8") as f: return f.read()
            
    def get_projects_list(self):
        content = self.get_official_links()
        projects = []
        current_project = None
        for line in content.split('\n'):
            if line.startswith("## "):
                if current_project: projects.append(current_project)
                current_project = {"name": line.replace("## ", "").strip()}
            elif current_project and ":" in line:
                key, val = line.split(":", 1)
                current_project[key.strip().lower()] = val.strip()
        if current_project: projects.append(current_project)
        return projects
    def init_item_assets(self, folder_id: str, item_id: str):
        history = self.list_history()
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
        self.save_history(history)
        return manifest_path

    def upload_item_asset(self, folder_id: str, item_id: str, file_name: str, file_content: bytes, asset_category: str, asset_role: str = ""):
        # Sanitizar nome
        clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '-', file_name).lower()
        clean_name = re.sub(r'-+', '-', clean_name).strip('-')
        
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
            
        manifest["files"]["prompts"].append({
            "text": prompt_text,
            "added_at": datetime.now().isoformat()
        })
        
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
