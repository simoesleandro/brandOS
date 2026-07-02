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

    def add_metrics_snapshot(self, folder_id: str, item_id: str, snapshot_data: dict):
        history = self.list_history()
        date_prefix = folder_id[:10]
        json_path = os.path.join(self.registry_dir, "publication-log.json")
        
        updated = False
        for entry in history:
            if entry.get("date") == date_prefix or entry.get("id") == folder_id:
                for item in entry.get("items", []):
                    if item.get("id") == item_id:
                        current_metrics = item.get("metrics", {})
                        
                        if current_metrics and "latest" not in current_metrics and "snapshots" not in current_metrics:
                            legacy_snapshot = dict(current_metrics)
                            import uuid
                            legacy_snapshot["id"] = str(uuid.uuid4())
                            legacy_snapshot["label"] = "inicial"
                            
                            cap_date = legacy_snapshot.get("captured_at")
                            if not cap_date:
                                cap_date = item.get("published_at", "")
                                if not cap_date:
                                    from datetime import datetime
                                    cap_date = datetime.now().strftime("%Y-%m-%d")
                                else:
                                    cap_date = cap_date[:10]
                            legacy_snapshot["captured_at"] = cap_date
                            
                            current_metrics = {
                                "latest": legacy_snapshot,
                                "snapshots": [legacy_snapshot]
                            }
                        elif not current_metrics:
                            current_metrics = {
                                "latest": {},
                                "snapshots": []
                            }
                        
                        try:
                            impressions = int(snapshot_data.get("impressions", 0) or 0)
                            reach = int(snapshot_data.get("reach", 0) or 0)
                            reactions = int(snapshot_data.get("reactions", 0) or 0)
                            comments = int(snapshot_data.get("comments", 0) or 0)
                            shares = int(snapshot_data.get("shares", 0) or 0)
                            saves = int(snapshot_data.get("saves", 0) or 0)
                            sends = int(snapshot_data.get("sends", 0) or 0)
                            profile_views = int(snapshot_data.get("profile_views", 0) or 0)
                            followers_gained = int(snapshot_data.get("followers_gained", 0) or 0)
                        except ValueError:
                            raise ValueError("Métricas devem ser numéricas")
                            
                        total_engagements = reactions + comments + shares + saves + sends
                        
                        engagement_rate_by_impressions = 0.0
                        if impressions > 0:
                            engagement_rate_by_impressions = round((total_engagements / impressions) * 100, 2)
                            
                        engagement_rate_by_reach = 0.0
                        if reach > 0:
                            engagement_rate_by_reach = round((total_engagements / reach) * 100, 2)
                            
                        profile_view_rate_by_reach = 0.0
                        if reach > 0:
                            profile_view_rate_by_reach = round((profile_views / reach) * 100, 2)
                            
                        label = str(snapshot_data.get("label", "personalizado"))
                        custom_label = str(snapshot_data.get("custom_label", "")).strip()
                        if label == "personalizado" and custom_label:
                            label = custom_label
                        elif label == "personalizado":
                            label = "custom"
                            
                        captured_at = str(snapshot_data.get("captured_at", "")).strip()
                        if not captured_at:
                            from datetime import datetime
                            captured_at = datetime.now().strftime("%Y-%m-%d")
                            
                        import uuid
                        new_snapshot = {
                            "id": str(uuid.uuid4()),
                            "label": label,
                            "captured_at": captured_at,
                            "impressions": impressions,
                            "reach": reach,
                            "reactions": reactions,
                            "comments": comments,
                            "shares": shares,
                            "saves": saves,
                            "sends": sends,
                            "profile_views": profile_views,
                            "followers_gained": followers_gained,
                            "total_engagements": total_engagements,
                            "engagement_rate_by_impressions": engagement_rate_by_impressions,
                            "engagement_rate_by_reach": engagement_rate_by_reach,
                            "profile_view_rate_by_reach": profile_view_rate_by_reach,
                            "notes": snapshot_data.get("notes", "")
                        }
                        
                        current_metrics["latest"] = new_snapshot
                        current_metrics["snapshots"].append(new_snapshot)
                        
                        item["metrics"] = current_metrics
                        updated = True
                        break
                if updated:
                    break
        
        if updated:
            import json
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            self._rebuild_markdown_log(history)
        else:
            raise Exception("Item não encontrado no publication-log.json")


    def get_dashboard_metrics(self):
        history = self.list_history()
        
        total_weeks = len(history)
        total_items = 0
        ready_items = 0
        published_items = 0
        pending_items = 0
        linked_assets_items = 0
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
                    
                    if status == "used_as_asset":
                        linked_assets_items += 1
                    elif status == "ready_to_publish":
                        ready_items += 1
                        queue.append({"project": entry.get("project"), "title": item.get("title"), "status": status, "folder_id": folder_id, "item_id": item.get("id")})
                    elif status == "published":
                        published_items += 1
                        action_text = f"{item.get('title')} publicado"
                        if item.get("assets"):
                            action_text = f"{item.get('title')} publicado no LinkedIn com carrossel anexado"
                        recent_activity.append({"action": action_text, "project": entry.get("project"), "time": item.get("published_at")})
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
            "linked_assets_items": linked_assets_items,
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
        gen_dir = os.path.join(self.base_dir, "data", "generated", folder_id)
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
        
        gen_dir = os.path.join(self.base_dir, "data", "generated", folder_id)
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

    def generate_snapshot_analysis(self, folder_id: str, item_id: str, snapshot_data: dict) -> str:
        history = self.list_history()
        date_prefix = folder_id[:10]
        
        target_item = None
        target_project = ""
        for entry in history:
            if entry.get("date") == date_prefix or entry.get("id") == folder_id:
                target_project = entry.get("project", "")
                for item in entry.get("items", []):
                    if item.get("id") == item_id:
                        target_item = item
                        break
                if target_item:
                    break
                    
        if not target_item:
            raise Exception("Item não encontrado no publication-log.json")
            
        current_metrics = target_item.get("metrics", {})
        snapshots = current_metrics.get("snapshots", []) if current_metrics else []
        
        previous_snapshot_str = "Nenhum snapshot anterior encontrado."
        if snapshots:
            prev = snapshots[-1]
            previous_snapshot_str = (
                f"Label: {prev.get('label', '')}\n"
                f"Data: {prev.get('captured_at', '')}\n"
                f"Impressões: {prev.get('impressions', 0)}\n"
                f"Alcance: {prev.get('reach', 0)}\n"
                f"Engajamentos: {prev.get('total_engagements', 0)}\n"
                f"Taxa por Impressões: {prev.get('engagement_rate_by_impressions', 0)}%\n"
                f"Taxa por Alcance: {prev.get('engagement_rate_by_reach', 0)}%\n"
                f"Visitas ao Perfil: {prev.get('profile_views', 0)}\n"
            )
            
        current_snapshot_str = (
            f"Label: {snapshot_data.get('label', '')}\n"
            f"Data: {snapshot_data.get('captured_at', '')}\n"
            f"Impressões: {snapshot_data.get('impressions', 0)}\n"
            f"Alcance: {snapshot_data.get('reach', 0)}\n"
            f"Engajamentos: {snapshot_data.get('total_engagements', 0)}\n"
            f"Taxa por Impressões: {snapshot_data.get('engagement_rate_by_impressions', 0)}%\n"
            f"Taxa por Alcance: {snapshot_data.get('engagement_rate_by_reach', 0)}%\n"
            f"Visitas ao Perfil: {snapshot_data.get('profile_views', 0)}\n"
        )
        
        diffs_str = "Indisponível (primeiro snapshot)"
        if snapshots:
            prev = snapshots[-1]
            d_imp = float(snapshot_data.get('impressions', 0)) - float(prev.get('impressions', 0))
            d_reach = float(snapshot_data.get('reach', 0)) - float(prev.get('reach', 0))
            d_eng = float(snapshot_data.get('total_engagements', 0)) - float(prev.get('total_engagements', 0))
            d_tx_imp = float(snapshot_data.get('engagement_rate_by_impressions', 0)) - float(prev.get('engagement_rate_by_impressions', 0))
            d_tx_reach = float(snapshot_data.get('engagement_rate_by_reach', 0)) - float(prev.get('engagement_rate_by_reach', 0))
            d_vis = float(snapshot_data.get('profile_views', 0)) - float(prev.get('profile_views', 0))
            
            diffs_str = (
                f"Impressões: {'+' if d_imp>0 else ''}{d_imp}\n"
                f"Alcance: {'+' if d_reach>0 else ''}{d_reach}\n"
                f"Engajamentos: {'+' if d_eng>0 else ''}{d_eng}\n"
                f"Taxa (Imp): {'+' if d_tx_imp>0 else ''}{round(d_tx_imp, 2)}%\n"
                f"Taxa (Alc): {'+' if d_tx_reach>0 else ''}{round(d_tx_reach, 2)}%\n"
                f"Visitas: {'+' if d_vis>0 else ''}{d_vis}\n"
            )
            
        system_prompt = (
            "Você é o Analytics Agent do BrandOS. "
            "Analise a performance de uma publicação no LinkedIn com base nos snapshots abaixo. "
            "Instruções estritas:\n"
            "- Escreva em português brasileiro.\n"
            "- Seja direto e objetivo.\n"
            "- NÃO invente dados de forma alguma.\n"
            "- Se a amostra for pequena (ex: poucas impressões/interações), deixe isso claro usando tom prudente (ex: 'sinal inicial positivo', 'amostra pequena', 'ponto de atenção'). Não use exageros como 'grande sucesso', 'excelente performance', 'viralizou'.\n"
            "- Compare o snapshot atual com o anterior, focando no que mudou.\n"
            "- Caso não haja snapshot anterior, deixe claro no texto: 'Como ainda não há snapshot anterior, esta leitura serve como linha de base.' e faça a leitura do estado atual.\n"
            "- Escreva um texto contínuo de 1 a 2 parágrafos no máximo.\n"
            "- NÃO use bullet points.\n"
            "- NÃO coloque títulos.\n"
            "- Aborde: 1) leitura principal, 2) sinal positivo, 3) ponto de atenção, 4) próxima ação prática."
        )
        
        user_prompt = f"""
Dados da peça:
Projeto: {target_project}
Peça: {target_item.get('title', '')}
Tipo: {target_item.get('type', '')}
Status: {target_item.get('status', '')}

Snapshot anterior:
{previous_snapshot_str}

Snapshot atual (Não Salvo Ainda):
{current_snapshot_str}

Diferenças calculadas:
{diffs_str}
"""
        from app.core.llm_client import LLMClient
        try:
            client = LLMClient()
            analysis = client.generate_content(system_prompt, user_prompt)
            return analysis.strip()
        except Exception as e:
            print(f"Erro no Gemini: {e}")
            raise e

