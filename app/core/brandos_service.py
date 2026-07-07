import os
import re
import json
from datetime import datetime
from app.workflows.weekly_workflow import run_weekly_workflow
from app.core.services.service_container import create_brandos_services

class BrandOSService:
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.registry_dir = os.path.join(self.base_dir, "data", "registry")
        self.knowledge_dir = os.path.join(self.base_dir, "data", "knowledge")
        self.inbox_dir = os.path.join(self.base_dir, "data", "inbox")
        self.generated_dir = os.path.join(self.base_dir, "data", "generated")
        self.assets_dir = os.path.join(self.base_dir, "data", "assets")
        os.makedirs(self.assets_dir, exist_ok=True)
        from app.core.llm_client import LLMClient
        self.llm = LLMClient()
        services = create_brandos_services(base_dir, llm_client=self.llm)
        self.history_repo = services.history_repo
        self.asset_service = services.asset_service
        self.briefing_service = services.briefing_service
        self.calendar_service = services.calendar_service
        self.cmo_service = services.cmo_service
        self.learning_service = services.learning_service
        self.ops_service = services.ops_service
        self.operating_loop_service = services.operating_loop_service
        self.publication_service = services.publication_service
        
        # self._sync_generated_to_history()  # Removed to prevent writing on GET

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
                
            if not re.match(r"^\d{4}-\d{2}-\d{2}", folder):
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
            self.save_history(history)


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
        return self.history_repo.load()

    def save_history(self, history: list) -> None:
        """Salva o history no publication-log.json e reconstrói o markdown."""
        self.history_repo.save(history)

    def update_item_status(self, folder_id: str, item_id: str, new_status: str):
        """Atualiza o status de um item específico."""
        history = self.list_history()
        date_prefix = folder_id[:10]
        
        updated = False
        target_item = None
        for entry in history:
            if entry.get("date") == date_prefix or entry.get("id") == folder_id:
                for item in entry.get("items", []):
                    if self._get_item_identifier(item) == item_id:
                        old_status = item.get("status")
                        item["status"] = new_status
                        target_item = item
                        if new_status == "published":
                            if old_status != "published" or not item.get("published_at"):
                                from datetime import datetime
                                item["published_at"] = datetime.now().isoformat()
                        updated = True
                        break
                
                if updated:
                    entry["status"] = self._recalculate_week_status(entry)
                    break
                
        if updated:
            self.save_history(history)
            
            # Auto-start tracking if transitioning to published
            if new_status == "published" and target_item:
                is_main, _ = self._is_main_publication(target_item)
                # Don't track assets
                is_asset = target_item.get("status") == "used_as_asset" or target_item.get("linked_to_item_id") or target_item.get("asset_role")
                if is_main and not is_asset:
                    if not target_item.get("post_publish_tracking_status"):
                        self.start_post_publish_tracking(item_id=item_id, confirm=True)

    def get_editorial_calendar(self) -> list:
        """Retorna uma lista de peças publicáveis para a Agenda Editorial."""
        return self.calendar_service.get_editorial_calendar()

    def update_item_schedule(self, folder_id: str, item_id: str, schedule_data: dict):
        """Atualiza os dados de agendamento de uma peça."""
        return self.calendar_service.update_item_schedule(folder_id, item_id, schedule_data)

    def add_metrics_snapshot(self, folder_id: str, item_id: str, snapshot_data: dict):
        return self.calendar_service.add_metrics_snapshot(folder_id, item_id, snapshot_data)


    def get_dashboard_metrics(self):
        return self.ops_service.get_dashboard_metrics()

    def get_today_operating_loop(self) -> dict:
        return self.operating_loop_service.get_today_operating_loop()
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
            is_main_publication, _ = self._is_main_publication(item)
                        
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
        return self.asset_service.init_item_assets(folder_id, item_id)

    def upload_item_asset(self, folder_id: str, item_id: str, file_name: str, file_content: bytes, asset_category: str, asset_role: str = ""):
        return self.asset_service.upload_item_asset(folder_id, item_id, file_name, file_content, asset_category, asset_role)

    def add_item_asset_prompt(self, folder_id: str, item_id: str, prompt_text: str):
        return self.asset_service.add_item_asset_prompt(folder_id, item_id, prompt_text)

    def get_recommended_prompts(self, folder_id: str):
        return self.asset_service.get_recommended_prompts(folder_id)

    def import_recommended_prompt(self, folder_id: str, item_id: str, filename: str):
        return self.asset_service.import_recommended_prompt(folder_id, item_id, filename)

    def delete_item_asset(self, folder_id: str, item_id: str, category: str, filename: str):
        return self.asset_service.delete_item_asset(folder_id, item_id, category, filename)

    def delete_item_prompt(self, folder_id: str, item_id: str, prompt_id: str = None, prompt_index: int = None):
        return self.asset_service.delete_item_prompt(folder_id, item_id, prompt_id, prompt_index)

    def generate_snapshot_analysis(self, folder_id: str, item_id: str, snapshot_data: dict) -> str:
        return self.calendar_service.generate_snapshot_analysis(folder_id, item_id, snapshot_data)

    def import_linkedin_analytics(self, folder_id: str, item_id: str, file_path: str, original_filename: str) -> dict:
        return self.calendar_service.import_linkedin_analytics(folder_id, item_id, file_path, original_filename)
    def generate_cmo_recommendation(self):
        return self.cmo_service.generate_cmo_recommendation()
    def save_cmo_recommendation_as_briefing(self, recommendation_text: str) -> str:
        return self.briefing_service.save_cmo_recommendation_as_briefing(recommendation_text)

    def list_briefings(self) -> list:
        return self.briefing_service.list_briefings()

    def read_briefing(self, filename: str) -> str:
        return self.briefing_service.read_briefing(filename)

    def prepare_week_from_briefing(self, filename: str) -> dict:
        return self.briefing_service.prepare_week_from_briefing(filename)

    def generate_week_from_briefing(self, filename: str, options: dict) -> dict:
        return self.briefing_service.generate_week_from_briefing(filename, options)

    def get_generated_week_details(self, folder_name: str) -> dict:
        """
        Retorna os detalhes da semana gerada.
        """
        import os
        folder_name = os.path.basename(folder_name)
        folder_path = os.path.join(self.base_dir, "data", "generated", folder_name)
        
        if not os.path.exists(folder_path):
            raise ValueError(f"A semana gerada '{folder_name}' não existe.")
            
        result = {
            "folder_name": folder_name,
            "briefing_source": "Desconhecida",
            "planned_week_start": "",
            "warnings": [],
            "auxiliary_files": {},
            "posts": {
                "segunda": None,
                "quarta": None,
                "sexta": None
            },
            "general_status": "generated"
        }
        
        # Load registry to find matching items
        log_items = []
        try:
            history = self.history_repo.load()
            log_items = [item for _, item in self.history_repo.iter_items(history)]
        except Exception as e:
            result["warnings"].append(f"Erro ao carregar registry: {str(e)}")
                
        # Filter items for this generated folder
        folder_items = [i for i in log_items if i.get("source") == "generated_from_briefing" and i.get("generated_folder") == folder_name]
        
        if folder_items:
            result["briefing_source"] = folder_items[0].get("briefing_file", "Desconhecida")
            result["planned_week_start"] = folder_items[0].get("planned_week_start", "")
            
        approved_count = 0
        total_posts = 0
        
        # Map posts
        post_mapping = {
            "segunda": "03-post-segunda.md",
            "quarta": "04-post-quarta.md",
            "sexta": "05-post-sexta.md"
        }
        
        for day, filename in post_mapping.items():
            file_path = os.path.join(folder_path, filename)
            content = ""
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    content = f"Erro ao ler arquivo: {str(e)}"
            else:
                result["warnings"].append(f"Arquivo {filename} não encontrado.")
                
            # Find item in registry
            item = next((i for i in folder_items if i.get("planned_day") == day), None)
            
            if item:
                total_posts += 1
                if item.get("status") == "approved":
                    approved_count += 1
                    
            result["posts"][day] = {
                "file": filename,
                "content": content,
                "status": item.get("status", "unknown") if item else "unknown",
                "title": item.get("title", f"Post {day}") if item else f"Post {day}",
                "item_id": item.get("item_id") if item else None,
                "scheduled_date": item.get("scheduled_date") if item else None,
                "scheduled_time": item.get("scheduled_time") if item else None
            }
            
        # Calc general status
        if total_posts > 0:
            if approved_count == total_posts:
                result["general_status"] = "approved"
            elif approved_count > 0:
                result["general_status"] = "partially_approved"
            else:
                result["general_status"] = "generated"
                
        # Map auxiliary files
        aux_mapping = {
            "briefing": "01-briefing.md",
            "plano": "02-plano-editorial.md",
            "instrucoes": "06-instrucoes-publicacao.md",
            "prompts": "07-prompts-visuais.md"
        }
        
        for key, filename in aux_mapping.items():
            file_path = os.path.join(folder_path, filename)
            content = ""
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    content = f"Erro ao ler arquivo: {str(e)}"
            else:
                result["warnings"].append(f"Arquivo auxiliar {filename} não encontrado.")
                
            result["auxiliary_files"][key] = {
                "file": filename,
                "content": content
            }
            
        return result
        

    def discard_item(self, item_id: str, reason: str = "Descartado manualmente pelo usuário.", confirm: bool = True) -> dict:
        return self.publication_service.discard_item(item_id, reason, confirm)

    def update_item_content(self, item_id: str, content: str, source_note: str = "") -> dict:
        return self.publication_service.update_item_content(item_id, content, source_note)

    def approve_generated_post(self, folder_name: str, planned_day: str) -> dict:
        return self.publication_service.approve_generated_post(folder_name, planned_day)

    def approve_generated_week(self, folder_name: str) -> dict:
        return self.publication_service.approve_generated_week(folder_name)

    def schedule_post(self, item_id: str, scheduled_date: str, scheduled_time: str, confirm: bool) -> dict:
        return self.publication_service.schedule_post(item_id, scheduled_date, scheduled_time, confirm)
    def reschedule_post(self, item_id: str, scheduled_date: str, scheduled_time: str, confirm: bool) -> dict:
        return self.publication_service.reschedule_post(item_id, scheduled_date, scheduled_time, confirm)
    def unschedule_post(self, item_id: str, confirm: bool) -> dict:
        return self.publication_service.unschedule_post(item_id, confirm)
    def _is_asset(self, item: dict) -> bool:
        return (item.get("status") == "used_as_asset" or 
                bool(item.get("linked_to_item_id")) or 
                bool(item.get("asset_role")))
                
    def _is_main_publication(self, item: dict) -> tuple[bool, str]:
        # Excluir assets vinculados
        if item.get("status") == "used_as_asset" or item.get("linked_to_item_id") or item.get("asset_role"):
            return False, "Is asset"

        # Termos proibidos
        prohibited = [
            "briefing", "briefings", "cmo", "cmo-next-week", "next-week", "next week",
            "recommendation", "recommendations", "recomendacao", "recomendação",
            "instruções", "instrucoes", "instrucoes-publicacao", "instruções-publicação",
            "prompts-visuais", "prompts visuais", "plano-editorial", "plano editorial",
            "publication instructions", "primeiro-comentario", "primeiro comentário",
            "comment", "auxiliary", "support", "asset", "visual prompt"
        ]

        # Campos a verificar
        fields = [
            item.get("id", ""), item.get("item_id", ""), item.get("title", ""),
            item.get("type", ""), item.get("post_type", ""), item.get("role", ""),
            item.get("category", ""), item.get("source", ""), item.get("content_file", ""),
            item.get("generated_folder", ""), item.get("file", ""), item.get("filename", "")
        ]

        text_to_check = " ".join([str(f).lower() for f in fields if f])

        for term in prohibited:
            if term in text_to_check:
                return False, f"Prohibited term: {term}"

        # Evidência positiva
        planned_day = str(item.get("planned_day", "")).lower()
        if planned_day in ["segunda", "quarta", "sexta"]:
            return True, "Valid planned_day"

        for term in ["post-segunda", "post-quarta", "post-sexta"]:
            if term in str(item.get("id", "")).lower() or term in str(item.get("item_id", "")).lower() or term in str(item.get("content_file", "")).lower():
                return True, f"Valid post term in ID/file: {term}"

        type_fields = [str(item.get("type", "")).lower(), str(item.get("post_type", "")).lower()]
        for t in type_fields:
            if t in ["post", "linkedin_post", "main_post", "publication", "main_publication"]:
                return True, f"Valid post type: {t}"

        return False, "No positive evidence"

    def _get_item_identifier(self, item: dict) -> str | None:
        """Retorna o identificador de um item. Prefere item_id, fallback para id, senão None."""
        return item.get("item_id") or item.get("id")



    def generate_editorial_learning(self, item_id: str, confirm: bool = True, notes: str = None) -> dict:
        return self.learning_service.generate_editorial_learning(item_id, confirm, notes)
    def get_latest_strategic_memory(self) -> dict:
        return self.learning_service.get_latest_strategic_memory()
    def generate_strategic_memory(self, confirm: bool = True, window_days: int = 30, notes: str = None) -> dict:
        return self.learning_service.generate_strategic_memory(confirm, window_days, notes)
    def archive_cmo_recommendation(self, recommendation_id: str, confirm: bool = True) -> dict:
        return self.cmo_service.archive_cmo_recommendation(recommendation_id, confirm)

    def _validate_cmo_recommendation_specificity(self, text: str) -> bool:
        return self.cmo_service._validate_cmo_recommendation_specificity(text)
    def generate_cmo_recommendation_with_memory(self, confirm: bool = True, window_days: int = 30, notes: str = None) -> dict:
        return self.cmo_service.generate_cmo_recommendation_with_memory(confirm, window_days, notes)
    def edit_briefing(self, filename: str, new_content: str, confirm: bool = True) -> dict:
        return self.briefing_service.edit_briefing(filename, new_content, confirm)

    def approve_briefing(self, filename: str, confirm: bool = True, user: str = "BrandOS User") -> dict:
        return self.briefing_service.approve_briefing(filename, confirm, user)

    def archive_briefing(self, filename: str, confirm: bool = True, user: str = "BrandOS User") -> dict:
        return self.briefing_service.archive_briefing(filename, confirm, user)

    def create_briefing_from_cmo_recommendation(self, recommendation_id: str, confirm: bool = True, notes: str = None) -> dict:
        return self.briefing_service.create_briefing_from_cmo_recommendation(recommendation_id, confirm, notes)

    def mark_manual_published(self, item_id: str, payload: dict) -> dict:
        return self.publication_service.mark_manual_published(item_id, payload)
    def get_ops_dashboard(self) -> dict:
        return self.ops_service.get_ops_dashboard()
    def get_publication_assistant(self, item_id: str) -> dict:
        import os, json
        
        history = self.history_repo.load()
        target = None
        for entry in history:
            items_to_process = entry.get("items", []) if "items" in entry else [entry]
            for i in items_to_process:
                if self._get_item_identifier(i) == item_id:
                    target = i
                    break
            if target:
                break
                
        if not target:
            raise ValueError("Post não encontrado.")
            
        if target.get("status") == "used_as_asset" or target.get("linked_to_item_id") or target.get("asset_role"):
            raise ValueError("Assets vinculados não podem ser publicados como publicações principais.")
            
        if target.get("status") in ["generated", "edited"]:
            raise ValueError("Este post ainda precisa ser aprovado e agendado antes da publicação manual.")
            
        if target.get("status") == "approved":
            raise ValueError("Este post precisa ser agendado antes de entrar no assistente de publicação.")
            
        if target.get("status") not in ["scheduled", "publishing_ready", "published"]:
            raise ValueError("Este post não está agendado ou pronto para publicação.")
            
        assistant_data = {
            "item": target,
            "post_content": "",
            "instructions": "",
            "prompts": "",
            "linked_assets": [],
            "warning": None
        }
        
        # Load post content
        content_file = target.get("content_file")
        if content_file:
            path = os.path.join(self.base_dir, content_file)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    assistant_data["post_content"] = f.read()
            else:
                assistant_data["warning"] = "Arquivo de conteúdo não encontrado para este post."
        else:
            assistant_data["warning"] = "Item sem arquivo de conteúdo vinculado."
                    
        # Load auxiliary instructions if folder exists
        folder = target.get("generated_folder")
        if folder:
            base_folder = os.path.join(self.base_dir, "data", "generated", folder)
            inst_path = os.path.join(base_folder, "06-instrucoes-publicacao.md")
            if os.path.exists(inst_path):
                with open(inst_path, "r", encoding="utf-8") as f:
                    assistant_data["instructions"] = f.read()
            
            prompt_path = os.path.join(base_folder, "07-prompts-visuais.md")
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    assistant_data["prompts"] = f.read()
                    
        return assistant_data

    def mark_post_publishing_ready(self, item_id: str, confirm: bool) -> dict:
        return self.publication_service.mark_post_publishing_ready(item_id, confirm)

    def mark_post_published(self, item_id: str, confirm: bool, published_url: str = None, published_at: str = None) -> dict:
        return self.publication_service.mark_post_published(item_id, confirm, published_url, published_at)

    def undo_post_published(self, item_id: str, confirm: bool, reason: str = None) -> dict:
        return self.publication_service.undo_post_published(item_id, confirm, reason)

    def normalize_registry_item_ids(self) -> dict:
        return self.ops_service.normalize_registry_item_ids()

    def preview_invalid_items(self) -> dict:
        return self.ops_service.preview_invalid_items()

    def discard_items_bulk(self, item_ids: list, reason: str, confirm: bool) -> dict:
        return self.ops_service.discard_items_bulk(item_ids, reason, confirm)

    def start_post_publish_tracking(self, item_id: str, confirm: bool = True) -> dict:
        return self.publication_service.start_post_publish_tracking(item_id, confirm)
    def update_post_publish_tracking_status(self, item_id: str, tracking_status: str, confirm: bool = True) -> dict:
        return self.publication_service.update_post_publish_tracking_status(item_id, tracking_status, confirm)
