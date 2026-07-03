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

    def get_editorial_calendar(self) -> list:
        """Retorna uma lista de peças publicáveis para a Agenda Editorial."""
        history = self.list_history()
        calendar_items = []
        
        # Palavras-chave que indicam itens auxiliares (não são posts principais)
        ignore_keywords = [
            "instruction", "instrucoes", "instruções", 
            "comentario", "comentário", "comment", 
            "prompt", "checklist", "asset"
        ]
        
        for entry in history:
            folder_id = entry.get("id")
            project = entry.get("project", "")
            date_prefix = entry.get("date", "")
            
            for item in entry.get("items", []):
                # 1. Ignorar itens usados explicitamente como asset
                if item.get("status") == "used_as_asset":
                    continue
                    
                # 2. Ignorar itens auxiliares baseados no id, título ou arquivo
                item_id_lower = item.get("id", "").lower()
                title_lower = item.get("title", "").lower()
                file_lower = item.get("file", "").lower()
                
                is_auxiliary = False
                for kw in ignore_keywords:
                    if kw in item_id_lower or kw in title_lower or kw in file_lower:
                        is_auxiliary = True
                        break
                        
                if is_auxiliary:
                    continue
                
                calendar_items.append({
                    "folder_id": folder_id,
                    "item_id": item.get("id"),
                    "title": item.get("title", ""),
                    "project": project,
                    "type": item.get("type", ""),
                    "status": item.get("status", "draft"),
                    "scheduled_for": item.get("scheduled_for", ""),
                    "scheduled_time": item.get("scheduled_time", ""),
                    "published_at": item.get("published_at", ""),
                    "channel": item.get("channel", "linkedin"),
                    "priority": item.get("priority", "normal"),
                    "entry_date": date_prefix,
                    "url": f"/publications/{folder_id}/item/{item.get('id')}"
                })
        
        def sort_key(item):
            # Prioritize scheduled_for, then published_at, then entry_date
            date_key = item["scheduled_for"] or item["published_at"] or item["entry_date"]
            return date_key
            
        # Reverse sorting by date (newest first, or we can sort oldest first)
        # Usually editorial calendars want to see future stuff first or in chronological order.
        # We will sort descending for now, or ascending. Let's do descending.
        calendar_items.sort(key=lambda x: sort_key(x), reverse=True)
        return calendar_items

    def update_item_schedule(self, folder_id: str, item_id: str, schedule_data: dict):
        """Atualiza os dados de agendamento de uma peça."""
        history = self.list_history()
        date_prefix = folder_id[:10]
        json_path = os.path.join(self.registry_dir, "publication-log.json")
        
        updated = False
        for entry in history:
            if entry.get("date") == date_prefix or entry.get("id") == folder_id:
                for item in entry.get("items", []):
                    if item.get("id") == item_id:
                        if "scheduled_for" in schedule_data:
                            item["scheduled_for"] = schedule_data["scheduled_for"]
                        if "scheduled_time" in schedule_data:
                            item["scheduled_time"] = schedule_data["scheduled_time"]
                        if "channel" in schedule_data:
                            item["channel"] = schedule_data["channel"]
                        if "priority" in schedule_data:
                            item["priority"] = schedule_data["priority"]
                        if "schedule_notes" in schedule_data:
                            item["schedule_notes"] = schedule_data["schedule_notes"]
                        updated = True
                        break
                if updated:
                    break
                    
        if updated:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        else:
            print(f"[BrandOS] Item não encontrado para agendamento {folder_id} {item_id}")

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
            # Classificação rigorosa conforme regras de negócios
            is_linked_asset = False
            if item.get("status") == "used_as_asset":
                is_linked_asset = True
            elif item.get("linked_to_item_id"):
                is_linked_asset = True
            elif item.get("asset_role"):
                is_linked_asset = True
                
            is_main_publication = False
            if not is_linked_asset:
                item_type = item.get("type", "")
                if item_type in ["linkedin_post", "post", "article", "video"]:
                    is_main_publication = True
                elif item_type == "carousel":
                    if item.get("status") != "used_as_asset" and not item.get("linked_to_item_id"):
                        is_main_publication = True
                        
            item["is_main_publication"] = is_main_publication
            item["is_scheduled"] = bool(item.get("scheduled_for")) and item.get("status") != "published"
            
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

    def import_linkedin_analytics(self, folder_id: str, item_id: str, file_path: str, original_filename: str) -> dict:
        import pandas as pd
        import shutil
        from datetime import datetime
        import re
        
        # 1. Armazenar o arquivo em data/assets/{folder_id}-{item_id}/analytics/
        asset_folder_name = f"{folder_id}-{item_id}"
        analytics_dir = os.path.join(self.assets_dir, asset_folder_name, "analytics")
        os.makedirs(analytics_dir, exist_ok=True)
        
        # Sanitizar filename
        safe_filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', original_filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        final_filename = f"{timestamp}_{safe_filename}"
        
        dest_path = os.path.join(analytics_dir, final_filename)
        shutil.copy2(file_path, dest_path)
        
        # Atualizar manifest.json
        manifest_path = os.path.join(self.assets_dir, asset_folder_name, "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                
            if "files" not in manifest:
                manifest["files"] = {}
                
            if "analytics" not in manifest["files"]:
                manifest["files"]["analytics"] = []
                
            manifest["files"]["analytics"].append({
                "filename": final_filename,
                "original_filename": original_filename,
                "path": f"analytics/{final_filename}",
                "uploaded_at": datetime.now().isoformat(),
                "source": "linkedin_export",
                "status": "imported"
            })
            
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
                
        # 2. Ler arquivo e extrair métricas
        try:
            if original_filename.lower().endswith('.csv'):
                # LinkedIn usa CSV as vezes com header na linha 1 ou 2
                df = pd.read_csv(dest_path)
            else:
                df = pd.read_excel(dest_path)
        except Exception as e:
            print(f"Erro ao ler arquivo com pandas: {e}")
            raise Exception("Não foi possível ler o arquivo. Formato inválido ou corrompido.")
            
        found_metrics = {
            "impressions": 0,
            "reach": 0,
            "reactions": 0,
            "comments": 0,
            "shares": 0,
            "saves": 0,
            "sends": 0,
            "profile_views": 0,
            "followers_gained": 0
        }
        
        keywords = {
            "impressions": ["impressões", "impressions"],
            "reach": ["alcance", "usuários alcançados", "membros alcançados", "reach", "reached members"],
            "reactions": ["reações", "reactions", "gostei", "likes"],
            "comments": ["comentários", "comments", "comentarios"],
            "shares": ["compartilhamentos", "shares", "reposts", "republicações"],
            "saves": ["salvamentos", "saves"],
            "sends": ["envios", "sends"],
            "profile_views": ["visualizações de perfil", "profile views", "profile visits"],
            "followers_gained": ["seguidores obtidos", "new followers", "followers gained"]
        }
        
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        def extract_value(df, keys):
            for col in df.columns:
                for k in keys:
                    if k in col:
                        val = pd.to_numeric(df[col], errors='coerce').sum()
                        if not pd.isna(val) and val > 0:
                            return int(val)
            
            for i, row in df.iterrows():
                row_vals = [str(v).lower().strip() for v in row.values]
                for j, v in enumerate(row_vals):
                    for k in keys:
                        if k in v:
                            if j + 1 < len(row.values):
                                val = pd.to_numeric(row.values[j+1], errors='coerce')
                                if not pd.isna(val):
                                    return int(val)
                            if i + 1 < len(df):
                                val = pd.to_numeric(df.iloc[i+1, j], errors='coerce')
                                if not pd.isna(val):
                                    return int(val)
            return 0
            
        for metric_key, keys in keywords.items():
            found_metrics[metric_key] = extract_value(df, keys)
            
        total_engagements = sum([
            found_metrics["reactions"],
            found_metrics["comments"],
            found_metrics["shares"],
            found_metrics["saves"],
            found_metrics["sends"]
        ])
        
        found_metrics["total_engagements"] = total_engagements
        
        if found_metrics["impressions"] == 0 and found_metrics["reach"] == 0 and total_engagements == 0:
            raise Exception("O arquivo foi lido, mas o BrandOS não conseguiu identificar as métricas principais. Verifique se o arquivo é o export correto do LinkedIn.")
            
        # Add original filename to the result for display
        found_metrics["source_filename"] = original_filename
        
        return found_metrics
    def generate_cmo_recommendation(self):
        """
        Carrega contexto histórico, agenda e telemetria,
        aciona o LLM (CMO Agent) e salva a recomendação.
        """
        print("[CMO] Chamando BrandOSService.generate_cmo_recommendation()")
        
        from app.config import config
        print(f"[CMO] GEMINI_API_KEY configurada: {bool(config.API_KEY)}")

        try:
            from app.core.llm_client import LLMClient
            print("[CMO] Instanciando LLMClient")
            llm = LLMClient()
        except ValueError as e:
            print("[CMO][ERROR]", repr(e))
            raise Exception("gemini_api_key_missing")
        except Exception as e:
            print("[CMO][ERROR]", repr(e))
            raise Exception("gemini_client_error")
            
        import datetime
        now = datetime.datetime.now()
        
        # 1. Carregar Publication Log (Agenda e Histórico)
        print("[CMO] Carregando publication-log.json")
        try:
            history = self.list_history()
        except Exception as e:
            print("[CMO][ERROR]", repr(e))
            raise Exception("context_build_error")
            
        print("[CMO] Montando contexto")
        # Resumir contexto do histórico para não exceder limites absurdos
        # Vamos pegar as últimas 4 semanas geradas
        recent_history = history[-4:] if len(history) > 4 else history
        
        context_str = f"Data atual do sistema: {now.strftime('%Y-%m-%d %H:%M')}\n\n"
        context_str += "=== HISTÓRICO RECENTE DE SEMANAS (AGENDA E STATUS) ===\n"
        for week in recent_history:
            context_str += f"- Semana: {week.get('date', '')} | Projeto: {week.get('project', '')} | Tema: {week.get('theme', '')}\n"
            for item in week.get("items", []):
                # Ignorar peças auxiliares para o CMO
                is_linked_asset = False
                if item.get("status") == "used_as_asset" or item.get("linked_to_item_id") or item.get("asset_role"):
                    is_linked_asset = True
                
                is_main_publication = False
                if not is_linked_asset:
                    item_type = item.get("type", "")
                    if item_type in ["linkedin_post", "post", "article", "video"]:
                        is_main_publication = True
                    elif item_type == "carousel":
                        if item.get("status") != "used_as_asset" and not item.get("linked_to_item_id"):
                            is_main_publication = True
                            
                if is_main_publication:
                    status = item.get("status", "draft")
                    metrics = item.get("metrics", {}).get("latest", {})
                    scheduled_for = item.get("scheduled_for", "Sem data")
                    context_str += f"  - Peça principal: {item.get('title')} | Status: {status} | Data: {scheduled_for}\n"
                    if metrics:
                        impressions = metrics.get('impressions', 0)
                        engagements = metrics.get('total_engagements', 0)
                        context_str += f"    Métricas recentes: {impressions} impressões, {engagements} engajamentos\n"
        
        # 2. Carregar arquivos de knowledge se existirem
        print("[CMO] Carregando knowledge files")
        def load_knowledge_file(filename):
            path = os.path.join(self.knowledge_dir, filename)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception as e:
                    print(f"[CMO][ERROR] Falha ao ler {filename}:", repr(e))
            return ""

        context_str += "\n=== PROJETOS CONHECIDOS ===\n"
        context_str += load_knowledge_file("projetos.md")
        
        context_str += "\n=== REGRAS EDITORIAIS ===\n"
        context_str += load_knowledge_file("regras-editoriais-por-projeto.md")
        
        context_str += "\n=== HISTÓRICO DE POSTAGENS ===\n"
        context_str += load_knowledge_file("historico-postagens.md")
        
        context_str += "\n=== CONTINUIDADE DE CONTEÚDO ===\n"
        context_str += load_knowledge_file("continuidade-conteudo.md")

        system_prompt = """Você é o CMO Agent do BrandOS, um sistema operacional editorial para marca pessoal.

Sua função é recomendar a próxima semana editorial com base no histórico real do usuário.

Regras:
- Não invente métricas.
- Não invente projetos.
- Não recomende repetir o mesmo tema se o histórico indicar saturação. Cuidado especial com a repetição do projeto "Sentinela RJ" ou o projeto mais recente: avalie se vale continuar ou alternar, e justifique.
- Antes de recomendar a próxima semana, verifique se existem publicações principais pendentes, em rascunho ou agendadas na semana atual. Se existirem, mencione isso no diagnóstico e recomende concluir ou reagendar essas peças antes de executar o novo plano.
- Leitura de telemetria: Diferencie baixo alcance/volume de engajamento proporcional. Se o alcance for baixo mas o engajamento for bom, diga que é um "sinal inicial positivo" de uma "amostra pequena". Não chame de "baixa telemetria" ou "fracasso" quando a taxa proporcional for boa.
- Mantenha prudência com poucos dados: use termos como "sinal inicial", "amostra pequena", "ainda não permite conclusão forte", "indício". Evite palavras como "sucesso", "fracasso" ou "alta performance" com amostras pequenas.
- Priorize consistência, aprendizado público e construção de autoridade.
- O usuário publica principalmente no LinkedIn.
- O tom deve ser profissional, direto e estratégico.
- Não escrever posts completos nesta etapa.
- Gerar apenas recomendação estratégica.

Responda em português brasileiro com esta exata estrutura:

# Recomendação CMO Agent — Próxima Semana

## 1. Diagnóstico atual

## 2. Projeto recomendado

## 3. Tema central sugerido

## 4. Justificativa estratégica

## 5. Risco de repetição ou saturação

## 6. Grade sugerida da semana
Segunda: 
Quarta: 
Sexta: 

## 7. Próxima ação recomendada"""

        user_prompt = f"Aqui está o contexto do histórico de conteúdo e telemetria atual:\n\n{context_str}\n\nGere a recomendação para a próxima semana."
        
        try:
            print("[CMO] Chamando Gemini")
            recommendation_text = llm.generate_content(system_prompt, user_prompt)
            print("[CMO] Resposta recebida")
        except Exception as e:
            print("[CMO][ERROR]", repr(e))
            raise Exception("gemini_generation_error")
            
        try:
            print("[CMO] Salvando recomendação")
            # Salvar no histórico
            cmo_dir = os.path.join(self.base_dir, "data", "generated", "cmo-recommendations")
            os.makedirs(cmo_dir, exist_ok=True)
            
            filename = now.strftime("%Y-%m-%d-%H%M-cmo-next-week.md")
            file_path = os.path.join(cmo_dir, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Data: {now.strftime('%Y-%m-%d %H:%M')}\nFonte: BrandOS\n\n{recommendation_text}")
        except Exception as e:
            print("[CMO][ERROR]", repr(e))
            raise Exception("save_file_error")
                
        return recommendation_text
    def save_cmo_recommendation_as_briefing(self, recommendation_text: str) -> str:
        """
        Salva a recomendação gerada pelo CMO Agent como um briefing estruturado
        em data/generated/briefings.
        """
        if not recommendation_text or not recommendation_text.strip():
            raise ValueError("Nenhuma recomendação disponível para salvar como briefing.")
            
        import datetime
        now = datetime.datetime.now()
        
        briefings_dir = os.path.join(self.base_dir, "data", "generated", "briefings")
        os.makedirs(briefings_dir, exist_ok=True)
        
        filename = now.strftime("%Y-%m-%d-%H%M-next-week-briefing.md")
        file_path = os.path.join(briefings_dir, filename)
        
        content = f"""# Briefing Editorial — Próxima Semana

Data de criação: {now.strftime('%Y-%m-%d %H:%M')}  
Fonte: CMO Agent  
Status: briefing_aprovado  

---

{recommendation_text.strip()}
"""
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"[CMO][ERROR] Falha ao salvar briefing: {repr(e)}")
            raise ValueError("Não foi possível salvar o briefing.")
            
        # Retornar caminho relativo amigável
        return f"data/generated/briefings/{filename}"

    def list_briefings(self) -> list:
        """
        Lê a pasta data/generated/briefings/ e retorna os briefings ordenados (mais recentes primeiro),
        extraindo metadados básicos do cabeçalho.
        """
        briefings_dir = os.path.join(self.base_dir, "data", "generated", "briefings")
        if not os.path.exists(briefings_dir):
            return []
            
        briefings = []
        for filename in os.listdir(briefings_dir):
            if filename.endswith(".md"):
                file_path = os.path.join(briefings_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    created_at = "Desconhecido"
                    source = "Desconhecida"
                    status = "Desconhecido"
                    
                    for line in lines[:10]:
                        if line.startswith("Data de criação:"):
                            created_at = line.replace("Data de criação:", "").strip()
                        elif line.startswith("Fonte:"):
                            source = line.replace("Fonte:", "").strip()
                        elif line.startswith("Status:"):
                            status = line.replace("Status:", "").strip()
                            
                    sort_key = filename
                    
                    briefings.append({
                        "filename": filename,
                        "created_at": created_at,
                        "source": source,
                        "status": status,
                        "sort_key": sort_key
                    })
                except Exception as e:
                    print(f"Erro ao ler briefing {filename}: {e}")
                    
        briefings.sort(key=lambda x: x["sort_key"], reverse=True)
        return briefings

    def read_briefing(self, filename: str) -> str:
        """
        Lê e retorna o conteúdo completo de um briefing, prevenindo path traversal.
        """
        import os
        filename = os.path.basename(filename) # Impede path traversal
        file_path = os.path.join(self.base_dir, "data", "generated", "briefings", filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError("Briefing não encontrado.")
            
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def prepare_week_from_briefing(self, filename: str) -> dict:
        """
        Lê o briefing e extrai os defaults para o modal de geração da semana.
        Na Fase 1, usaremos valores fallback sugeridos pelo usuário.
        """
        content = self.read_briefing(filename)
        
        from datetime import datetime, timedelta
        hoje = datetime.now()
        dias_para_segunda = 0 - hoje.weekday()
        if dias_para_segunda <= 0:
            dias_para_segunda += 7
        proxima_segunda = (hoje + timedelta(days=dias_para_segunda)).strftime("%Y-%m-%d")

        return {
            "projeto": "Sentinela RJ",
            "tema_central": "Bastidores da Coleta e Normalização de Dados do PNCP",
            "canal": "LinkedIn",
            "quantidade_posts": 3,
            "frequencia": "Segunda / Quarta / Sexta",
            "data_inicial": proxima_segunda
        }



    def generate_week_from_briefing(self, filename: str, options: dict) -> dict:
        """
        Gera a semana editorial usando o Gemini com base no briefing e nas opções do modal.
        """
        briefing_content = self.read_briefing(filename)

        import re
        import datetime
        
        # 1. Validate briefing status
        if not re.search(r'^\s*Status:\s*briefing_aprovado\s*$', briefing_content, re.IGNORECASE | re.MULTILINE):
            raise ValueError("Este briefing ainda não está aprovado para geração de semana editorial.")
            
        # 2. Validate date format (YYYY-MM-DD)
        data_inicial_str = options.get('start_date', '')
        try:
            dt = datetime.datetime.strptime(data_inicial_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Data inicial inválida. Use o formato YYYY-MM-DD.")

        # 3. Idempotency Check BEFORE Gemini
        import json
        log_path = os.path.join(self.base_dir, "data", "registry", "publication-log.json")
        log_data = {}
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
            except Exception:
                pass
                
        if "items" in log_data:
            existing = [item for item in log_data["items"] if item.get("source") == "generated_from_briefing" and item.get("briefing_file") == filename and item.get("planned_week_start") == data_inicial_str]
            has_seg = any(i.get("planned_day") == "segunda" for i in existing)
            has_qua = any(i.get("planned_day") == "quarta" for i in existing)
            has_sex = any(i.get("planned_day") == "sexta" for i in existing)
            
            if has_seg and has_qua and has_sex:
                # Retornar sucesso diretamente
                generated_folder = next((i.get("file", "").split("/")[1] for i in existing if "file" in i and i["file"].startswith("generated/")), "pasta_desconhecida")
                return {"status": "success", "folder": generated_folder, "message": "A semana editorial já havia sido gerada."}
        
        prompt = f'''Você é o Content Strategist e Copywriter do BrandOS.
Gere uma semana editorial a partir do briefing aprovado abaixo.

Regras:
- Não ignorar o briefing.
- Não repetir literalmente a recomendação do CMO.
- Transformar a estratégia em posts reais para LinkedIn.
- Manter tom profissional, humano e direto.
- Evitar cara de IA.
- Não inventar resultados do projeto.
- Não fazer acusações.
- No Sentinela RJ, preservar sempre a regra: anomalia não é acusação.
- Criar 3 posts: segunda, quarta e sexta.
- Cada post deve ter gancho, corpo e fechamento.
- Não pedir engajamento de forma artificial.
- Links GitHub/demo devem ficar no primeiro comentário ou instruções, não no corpo do post.
- Gerar também instruções de publicação separadas.
- Gerar conteúdo em português brasileiro.

Briefing aprovado:
{briefing_content}

Opções da geração:
Projeto: {options.get('projeto', 'Sentinela RJ')}
Tema: {options.get('tema_central')}
Data Inicial: {options.get('data_inicial')}
Frequência: {options.get('frequencia')}

Retorne a resposta em blocos claramente separáveis EXATAMENTE desta forma (use '## ' para cabeçalhos):

## PLANO EDITORIAL
...

## POST SEGUNDA
...

## POST QUARTA
...

## POST SEXTA
...

## INSTRUÇÕES DE PUBLICAÇÃO
...

## PROMPTS VISUAIS
...
'''
        
        print("[CMO] Chamando Gemini para gerar semana...")
        self.llm.connect()
        try:
            response_text = self.llm.generate_text(prompt)
        except Exception as e:
            print(f"[CMO] Erro na geração: {e}")
            raise Exception("Erro ao gerar semana com IA.")
            
        print("[CMO] Geração concluída. Fazendo parse dos blocos.")
        
        # Parse blocks
        blocks = {
            "PLANO EDITORIAL": "",
            "POST SEGUNDA": "",
            "POST QUARTA": "",
            "POST SEXTA": "",
            "INSTRUÇÕES DE PUBLICAÇÃO": "",
            "PROMPTS VISUAIS": ""
        }
        
        import re
        # Find all blocks starting with ## 
        pattern = re.compile(r'##\s+([^\n]+)\n(.*?)(?=\n##\s+|$)', re.DOTALL)
        matches = pattern.findall(response_text)
        
        parsed_correctly = False
        if len(matches) > 0:
            parsed_correctly = True
            for title, body in matches:
                title = title.strip().upper()
                if title in blocks:
                    blocks[title] = body.strip()
                elif "PLANO" in title:
                    blocks["PLANO EDITORIAL"] = body.strip()
                elif "SEGUNDA" in title:
                    blocks["POST SEGUNDA"] = body.strip()
                elif "QUARTA" in title:
                    blocks["POST QUARTA"] = body.strip()
                elif "SEXTA" in title:
                    blocks["POST SEXTA"] = body.strip()
                elif "INSTRU" in title:
                    blocks["INSTRUÇÕES DE PUBLICAÇÃO"] = body.strip()
                elif "PROMPT" in title:
                    blocks["PROMPTS VISUAIS"] = body.strip()
        
        # Check if basic posts were extracted
        if not blocks["POST SEGUNDA"] or not blocks["POST QUARTA"] or not blocks["POST SEXTA"]:
            parsed_correctly = False
            
        import uuid
        import datetime
        from slugify import slugify
        
        now = datetime.datetime.now()
        timestamp = now.strftime("%H%M")
        data_inicial = data_inicial_str
        slug = slugify(options.get('project_slug', 'projeto'))
        
        folder_name = f"{data_inicial}-semana-{slug}-{timestamp}"
        folder_path = os.path.join(self.base_dir, "data", "generated", folder_name)
        
        if os.path.exists(folder_path):
            folder_name = f"{data_inicial}-semana-{slug}-{timestamp}-{uuid.uuid4().hex[:4]}"
            folder_path = os.path.join(self.base_dir, "data", "generated", folder_name)
            
        os.makedirs(folder_path, exist_ok=True)
        
        print(f"[CMO] Salvando arquivos em {folder_path}...")
        
        if not parsed_correctly:
            # Fallback
            with open(os.path.join(folder_path, "01-briefing.md"), "w", encoding="utf-8") as f:
                f.write(briefing_content)
            with open(os.path.join(folder_path, "02-plano-editorial.md"), "w", encoding="utf-8") as f:
                f.write(response_text)
            
            warning = "Conteúdo não separado corretamente pela IA. Revisar geração."
            for idx, name in enumerate(["03-post-segunda.md", "04-post-quarta.md", "05-post-sexta.md", "06-instrucoes-publicacao.md", "07-prompts-visuais.md"]):
                with open(os.path.join(folder_path, name), "w", encoding="utf-8") as f:
                    f.write(warning)
        else:
            with open(os.path.join(folder_path, "01-briefing.md"), "w", encoding="utf-8") as f:
                f.write(briefing_content)
            with open(os.path.join(folder_path, "02-plano-editorial.md"), "w", encoding="utf-8") as f:
                f.write(blocks["PLANO EDITORIAL"])
            with open(os.path.join(folder_path, "03-post-segunda.md"), "w", encoding="utf-8") as f:
                f.write(blocks["POST SEGUNDA"])
            with open(os.path.join(folder_path, "04-post-quarta.md"), "w", encoding="utf-8") as f:
                f.write(blocks["POST QUARTA"])
            with open(os.path.join(folder_path, "05-post-sexta.md"), "w", encoding="utf-8") as f:
                f.write(blocks["POST SEXTA"])
            with open(os.path.join(folder_path, "06-instrucoes-publicacao.md"), "w", encoding="utf-8") as f:
                f.write(blocks["INSTRUÇÕES DE PUBLICAÇÃO"])
            
            prompts = blocks["PROMPTS VISUAIS"]
            if not prompts or len(prompts) < 10:
                prompts = "Prompts visuais pendentes de geração."
            with open(os.path.join(folder_path, "07-prompts-visuais.md"), "w", encoding="utf-8") as f:
                f.write(prompts)
                
        # Atualizar publication-log.json
        print("[CMO] Atualizando publication-log.json...")
        log_path = os.path.join(self.base_dir, "data", "registry", "publication-log.json")
        import json
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
            except Exception as e:
                print(f"[CMO] Erro ao carregar publication-log.json: {e}")
                log_data = {}
        else:
            log_data = {}
            
        if "items" not in log_data:
            log_data["items"] = []
            
        # Helper to parse initial date and add days for suggested_for
        from datetime import datetime, timedelta
        dt = datetime.strptime(data_inicial_str, "%Y-%m-%d")
            
        data_seg = dt.strftime("%Y-%m-%d")
        data_qua = (dt + timedelta(days=2)).strftime("%Y-%m-%d")
        data_sex = (dt + timedelta(days=4)).strftime("%Y-%m-%d")
        
        # Adicionar apenas posts principais
        new_items = [
            {
                "item_id": f"post-segunda-{timestamp}",
                "title": "Post segunda",
                "type": "linkedin_post",
                "status": "generated",
                "file": f"generated/{folder_name}/03-post-segunda.md",
                "project": options.get('project_slug', 'Sentinela RJ'),
                "created_at": now.isoformat(),
                "suggested_for": data_seg,
                "source": "generated_from_briefing",
                "briefing_file": filename,
                "planned_week_start": data_inicial_str,
                "planned_day": "segunda"
            },
            {
                "item_id": f"post-quarta-{timestamp}",
                "title": "Post quarta",
                "type": "linkedin_post",
                "status": "generated",
                "file": f"generated/{folder_name}/04-post-quarta.md",
                "project": options.get('project_slug', 'Sentinela RJ'),
                "created_at": now.isoformat(),
                "suggested_for": data_qua,
                "source": "generated_from_briefing",
                "briefing_file": filename,
                "planned_week_start": data_inicial_str,
                "planned_day": "quarta"
            },
            {
                "item_id": f"post-sexta-{timestamp}",
                "title": "Post sexta",
                "type": "linkedin_post",
                "status": "generated",
                "file": f"generated/{folder_name}/05-post-sexta.md",
                "project": options.get('project_slug', 'Sentinela RJ'),
                "created_at": now.isoformat(),
                "suggested_for": data_sex,
                "source": "generated_from_briefing",
                "briefing_file": filename,
                "planned_week_start": data_inicial_str,
                "planned_day": "sexta"
            }
        ]
        
        log_data["items"].extend(new_items)
        
        import shutil
        backup_dir = os.path.join(self.base_dir, "data", "registry", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = os.path.join(backup_dir, f"publication-log-{now.strftime('%Y%m%d-%H%M%S')}.json")
        
        if os.path.exists(log_path):
            try:
                shutil.copy2(log_path, backup_file)
            except Exception as e:
                raise Exception(f"Erro ao criar backup do publication-log.json: {e}")
                
        # Safe writing via temporary file
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(log_path), text=True)
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, log_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise Exception(f"Erro ao salvar publication-log.json de forma segura: {e}")
            
        print("[CMO] Semana gerada com sucesso.")
        return {"status": "success", "folder": folder_name}
