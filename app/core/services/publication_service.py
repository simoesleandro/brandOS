import os
import shutil
import datetime
import zoneinfo
from datetime import datetime as DateTime

from app.core.repositories.history_repository import HistoryRepository


class PublicationService:
    def __init__(self, base_dir: str, history_repo: HistoryRepository):
        self.base_dir = base_dir
        self.history_repo = history_repo

    def discard_item(self, item_id: str, reason: str = "Descartado manualmente pelo usuário.", confirm: bool = True) -> dict:
        if not confirm:
            raise ValueError("É necessário confirmar o descarte.")

        history = self.history_repo.load()
        _, target = self.history_repo.find_item(item_id, history)

        if not target:
            raise ValueError(f"Post {item_id} não encontrado.")
        if target.get("status") == "published":
            raise ValueError("Posts já publicados não podem ser descartados por este fluxo.")
        if self._is_asset(target):
            raise ValueError("Assets vinculados não podem ser descartados como publicações principais.")
        if target.get("status") not in ["draft", "generated", "edited", "approved", "scheduled", "publishing_ready", None, ""]:
            raise ValueError(f"O status '{target.get('status')}' não permite descarte.")

        old_status = target.get("status")
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_aware = DateTime.now(tz)
        now_str = now_aware.strftime("%Y-%m-%dT%H:%M:%S%z")

        target["status"] = "discarded"
        target["discarded_from_status"] = old_status
        target["discarded_at"] = now_str
        target["discarded_by"] = "human"
        target["discard_reason"] = reason
        target["updated_at"] = now_str

        for field in ["scheduled_at", "scheduled_date", "scheduled_time", "scheduled_for", "priority"]:
            target.pop(field, None)

        target.setdefault("discard_history", []).append({
            "event": "discarded",
            "from_status": old_status,
            "to_status": "discarded",
            "discarded_at": target["discarded_at"],
            "discarded_by": target["discarded_by"],
            "reason": reason
        })

        self.history_repo.save(history)
        return {"status": "success", "message": "Post descartado com sucesso."}

    def update_item_content(self, item_id: str, content: str, source_note: str = "") -> dict:
        history = self.history_repo.load()
        _, target_item = self.history_repo.find_item(item_id, history)

        if not target_item:
            raise ValueError(f"Item {item_id} não encontrado no histórico.")

        status = target_item.get("status", "")
        if status == "published":
            raise ValueError("Posts já publicados não podem ser editados por este fluxo. Crie uma nova versão ou use uma revisão futura.")
        if self._is_asset(target_item):
            raise ValueError("Assets vinculados não podem ser editados como publicações principais.")
        if not content or not content.strip():
            raise ValueError("Conteúdo não pode estar vazio.")

        content_file = target_item.get("content_file")
        if not content_file:
            raise ValueError("Item não possui arquivo de conteúdo associado.")

        file_path = os.path.join(self.base_dir, content_file)
        if not os.path.exists(file_path):
            raise ValueError(f"Arquivo {content_file} não encontrado fisicamente.")

        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d-%H%M%S")

        generated_folder = target_item.get("generated_folder")
        if generated_folder:
            backups_dir = os.path.join(self.base_dir, "data", "generated", generated_folder, "backups")
        else:
            backups_dir = os.path.join(os.path.dirname(file_path), "backups")

        os.makedirs(backups_dir, exist_ok=True)
        filename = os.path.basename(file_path)
        backup_file = os.path.join(backups_dir, f"{filename.replace('.md', '')}-{timestamp}.md")

        try:
            shutil.copy2(file_path, backup_file)
        except Exception as e:
            raise ValueError(f"Erro ao criar backup do markdown: {e}")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise ValueError(f"Erro ao salvar o conteúdo editado: {e}")

        target_item["content_version"] = "manual_final"
        target_item["content_source"] = "human_refined"
        target_item["updated_at"] = now.isoformat()
        target_item["last_edited_at"] = now.isoformat()
        target_item["edited_by"] = "human"
        target_item["editorial_source"] = "manual_edit"

        if status == "generated":
            target_item["status"] = "edited"

        note = source_note if source_note else "Texto refinado manualmente no BrandOS."
        target_item.setdefault("editorial_history", []).append({
            "event": "content_edited",
            "edited_at": now.isoformat(),
            "edited_by": "human",
            "source": "manual_edit",
            "backup_file": os.path.relpath(backup_file, self.base_dir).replace("\\", "/"),
            "note": note
        })

        self.history_repo.save(history)

        return {
            "status": "success",
            "message": "Versão final salva com sucesso.",
            "item_id": item_id,
            "new_status": target_item["status"],
            "content_version": "manual_final",
            "content_source": "human_refined",
            "backup_file": target_item["editorial_history"][-1]["backup_file"],
            "updated_at": target_item["updated_at"]
        }

    def approve_generated_post(self, folder_name: str, planned_day: str) -> dict:
        folder_name = os.path.basename(folder_name)
        if planned_day not in ["segunda", "quarta", "sexta"]:
            raise ValueError("Dia inválido. Use 'segunda', 'quarta' ou 'sexta'.")

        history = self.history_repo.load()
        target_item = None
        for _, item in self.history_repo.iter_items(history):
            if item.get("source") == "generated_from_briefing" and item.get("generated_folder") == folder_name and item.get("planned_day") == planned_day:
                target_item = item
                break

        if not target_item:
            raise ValueError("Post não encontrado no registry.")
        if target_item.get("status") == "approved":
            return {"status": "success", "message": "Post já estava aprovado."}
        if target_item.get("status") not in ["generated", "edited"]:
            raise ValueError(f"Status '{target_item.get('status')}' não permite aprovação.")

        now = datetime.datetime.now()
        target_item["status"] = "approved"
        target_item["updated_at"] = now.isoformat()
        target_item.setdefault("approved_at", now.isoformat())

        self.history_repo.save(history)
        return {"status": "success", "message": "Post aprovado com sucesso."}

    def approve_generated_week(self, folder_name: str) -> dict:
        folder_name = os.path.basename(folder_name)
        history = self.history_repo.load()
        items_to_approve = []
        for _, item in self.history_repo.iter_items(history):
            if item.get("source") == "generated_from_briefing" and item.get("generated_folder") == folder_name and item.get("planned_day") in ["segunda", "quarta", "sexta"]:
                items_to_approve.append(item)

        if not items_to_approve:
            raise ValueError("Nenhum post principal encontrado para esta semana.")

        now = datetime.datetime.now()
        updated = False
        for item in items_to_approve:
            if item.get("status") in ["generated", "edited"]:
                item["status"] = "approved"
                item["updated_at"] = now.isoformat()
                item.setdefault("approved_at", now.isoformat())
                updated = True

        if updated:
            self.history_repo.save(history)

        return {"status": "success", "message": "Semana aprovada com sucesso."}

    def schedule_post(self, item_id: str, scheduled_date: str, scheduled_time: str, confirm: bool) -> dict:
        if not confirm:
            raise ValueError("Confirmação necessária.")

        dt_str = self._validate_schedule_datetime(scheduled_date, scheduled_time, "agendamento")
        history = self.history_repo.load()
        _, target_item = self.history_repo.find_item(item_id, history)

        if not target_item:
            raise ValueError("Post não encontrado.")
        if self._is_asset(target_item):
            raise ValueError("Assets vinculados não podem ser agendados como publicações principais.")
        if target_item.get("status") == "scheduled":
            raise ValueError("Post já está agendado. Use a rota de reagendamento.")
        if target_item.get("status") != "approved":
            raise ValueError(f"Post possui status '{target_item.get('status')}'. É necessário estar 'approved' para agendar.")

        now = DateTime.now()
        target_item["status"] = "scheduled"
        target_item["scheduled_at"] = dt_str
        target_item["scheduled_date"] = scheduled_date
        target_item["scheduled_time"] = scheduled_time
        target_item["timezone"] = "America/Sao_Paulo"
        target_item["scheduled_by"] = "human"
        target_item["scheduled_source"] = "brandos_calendar"
        target_item["scheduled_at_created_at"] = now.isoformat()
        target_item["updated_at"] = now.isoformat()

        self.history_repo.save(history)
        return {"status": "success", "message": "Post agendado com sucesso."}

    def reschedule_post(self, item_id: str, scheduled_date: str, scheduled_time: str, confirm: bool) -> dict:
        if not confirm:
            raise ValueError("Confirmação necessária.")

        dt_str = self._validate_schedule_datetime(scheduled_date, scheduled_time, "reagendamento")
        history = self.history_repo.load()
        _, target_item = self.history_repo.find_item(item_id, history)

        if not target_item:
            raise ValueError("Post não encontrado.")
        if self._is_asset(target_item):
            raise ValueError("Assets vinculados não podem ser reagendados como publicações principais.")
        if target_item.get("status") != "scheduled":
            raise ValueError(f"Post possui status '{target_item.get('status')}'. É necessário estar 'scheduled' para reagendar.")
        if target_item.get("scheduled_date") == scheduled_date and target_item.get("scheduled_time") == scheduled_time:
            return {"status": "success", "message": "A data e horário são os mesmos, nenhuma alteração necessária."}

        now = DateTime.now()
        target_item["scheduled_at"] = dt_str
        target_item["scheduled_date"] = scheduled_date
        target_item["scheduled_time"] = scheduled_time
        target_item["updated_at"] = now.isoformat()
        target_item["rescheduled_at"] = now.isoformat()
        target_item["rescheduled_by"] = "human"

        self.history_repo.save(history)
        return {"status": "success", "message": "Post reagendado com sucesso."}

    def unschedule_post(self, item_id: str, confirm: bool) -> dict:
        if not confirm:
            raise ValueError("Confirmação necessária.")

        history = self.history_repo.load()
        _, target_item = self.history_repo.find_item(item_id, history)

        if not target_item:
            raise ValueError("Post não encontrado.")
        if self._is_asset(target_item):
            raise ValueError("Assets vinculados não podem ser manipulados como publicações principais.")
        if target_item.get("status") != "scheduled":
            raise ValueError(f"Post não está agendado (status atual: {target_item.get('status')}).")

        now = DateTime.now()
        target_item["status"] = "approved"
        for key in ["scheduled_at", "scheduled_date", "scheduled_time"]:
            target_item.pop(key, None)
        target_item["unscheduled_at"] = now.isoformat()
        target_item["unscheduled_by"] = "human"
        target_item["updated_at"] = now.isoformat()

        self.history_repo.save(history)
        return {"status": "success", "message": "Agendamento removido com sucesso."}

    def mark_post_publishing_ready(self, item_id: str, confirm: bool) -> dict:
        if not confirm:
            raise ValueError("Confirmação necessária.")

        history = self.history_repo.load()
        _, target_item = self.history_repo.find_item(item_id, history)

        if not target_item:
            raise ValueError("Post não encontrado.")
        if self._is_asset(target_item):
            raise ValueError("Assets vinculados não podem ser publicados como publicações principais.")
        if target_item.get("status") != "scheduled":
            raise ValueError(f"Post possui status '{target_item.get('status')}'. É necessário estar 'scheduled' para marcar como ready.")

        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_str = DateTime.now(tz).isoformat()
        target_item["status"] = "publishing_ready"
        target_item["publishing_ready_at"] = now_str
        target_item["updated_at"] = now_str

        self.history_repo.save(history)
        return {"status": "success", "message": "Post marcado como pronto para publicação."}

    def mark_post_published(self, item_id: str, confirm: bool, published_url: str = None, published_at: str = None) -> dict:
        if not confirm:
            raise ValueError("Confirmação necessária.")

        history = self.history_repo.load()
        _, target_item = self.history_repo.find_item(item_id, history)

        if not target_item:
            raise ValueError("Post não encontrado.")
        if self._is_asset(target_item):
            raise ValueError("Assets vinculados não podem ser publicados como publicações principais.")
        if target_item.get("status") not in ["scheduled", "publishing_ready"]:
            raise ValueError(f"Status '{target_item.get('status')}' não permitido para marcar como publicado.")

        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        if published_at:
            try:
                DateTime.fromisoformat(published_at.replace("Z", "+00:00"))
            except Exception:
                raise ValueError("Formato de published_at inválido.")
            pub_date = published_at
        else:
            pub_date = DateTime.now(tz).isoformat()

        target_item["status"] = "published"
        target_item["published_at"] = pub_date
        if published_url:
            target_item["published_url"] = published_url
        target_item["published_by"] = "human"
        target_item["publication_source"] = "manual_linkedin"
        target_item["updated_at"] = DateTime.now(tz).isoformat()

        self.history_repo.save(history)
        return {"status": "success", "message": "Post marcado como publicado."}

    def undo_post_published(self, item_id: str, confirm: bool, reason: str = None) -> dict:
        if not confirm:
            raise ValueError("Confirmação necessária.")

        history = self.history_repo.load()
        _, item = self.history_repo.find_item(item_id, history)

        if not item:
            raise ValueError("Post não encontrado.")
        if self._is_asset(item):
            raise ValueError("Assets vinculados não podem ser publicados como publicações principais.")
        if item.get("status") != "published":
            raise ValueError(f"Post possui status '{item.get('status')}'. É necessário estar 'published' para desfazer.")

        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_str = DateTime.now(tz).isoformat()
        item["status"] = "scheduled"
        item["unpublished_at"] = now_str
        item["unpublished_by"] = "human"
        if reason:
            item["unpublished_reason"] = reason
        item["updated_at"] = now_str

        item.setdefault("publication_history", []).append({
            "event": "undo_published",
            "from_status": "published",
            "to_status": "scheduled",
            "published_at": item.get("published_at"),
            "published_url": item.get("published_url"),
            "unpublished_at": now_str,
            "unpublished_by": "human",
            "reason": reason
        })

        self.history_repo.save(history)
        return {"status": "success", "message": "Marcação de publicação desfeita."}

    def _get_item_identifier(self, item: dict) -> str | None:
        """Retorna o identificador de um item. Prefere item_id, fallback para id, senão None."""
        return item.get("item_id") or item.get("id")

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

    def mark_manual_published(self, item_id: str, payload: dict) -> dict:
        import datetime, zoneinfo
        history = self.history_repo.load()
        if not history:
            raise ValueError("Registry vazio")
            
        target_item = None
        target_entry = None
        for entry in history:
            items_to_process = entry.get("items", []) if "items" in entry else [entry]
            for item in items_to_process:
                ident = self._get_item_identifier(item)
                if ident == item_id:
                    target_item = item
                    target_entry = entry
                    break
            if target_item:
                break
                
        if not target_item:
            raise ValueError("Item não encontrado")
            
        status = target_item.get("status")
        if status in ["published", "discarded", "used_as_asset"]:
            raise ValueError(f"Status inválido para publicação manual: {status}")
        if target_item.get("linked_to_item_id") or target_item.get("asset_role"):
            raise ValueError("Não é possível publicar um asset vinculado")
            
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now = datetime.datetime.now(tz).isoformat()
        
        previous_status = target_item.get("status")
        
        target_item["status"] = "published"
        target_item["previous_status"] = previous_status
        target_item["published_at"] = payload.get("published_at") or now
        if payload.get("published_url"):
            target_item["published_url"] = payload.get("published_url")
            
        target_item["published_by"] = "human"
        target_item["publication_source"] = "manual_linkedin"
        target_item["manual_override"] = True
        target_item["updated_at"] = now
        
        pub_history = target_item.get("publication_history", [])
        pub_history.append({
            "event": "manual_mark_published",
            "timestamp": now,
            "previous_status": previous_status,
            "new_status": "published"
        })
        target_item["publication_history"] = pub_history
        
        self.history_repo.save(history)
        return target_item

    def start_post_publish_tracking(self, item_id: str, confirm: bool = True) -> dict:
        if not confirm:
            return {"status": "error", "message": "Confirmação necessária."}
            
        history = self.history_repo.load()
        target_item = None
        
        for entry in history:
            for item in entry.get("items", []):
                if self._get_item_identifier(item) == item_id:
                    target_item = item
                    break
            if target_item:
                break
                
        if not target_item:
            return {"status": "error", "message": "Item não encontrado."}
            
        if target_item.get("status") != "published":
            return {"status": "error", "message": "Item precisa estar publicado para iniciar acompanhamento."}
            
        is_main, reason = self._is_main_publication(target_item)
        if not is_main and (target_item.get("status") == "used_as_asset" or target_item.get("linked_to_item_id") or target_item.get("asset_role")):
            return {"status": "error", "message": "Não é possível iniciar acompanhamento em asset vinculado."}
            
        if target_item.get("post_publish_tracking_status"):
            # Idempotent
            return {"status": "success", "message": "Acompanhamento já existente."}
            
        from datetime import datetime, timedelta
        
        published_at_str = target_item.get("published_at")
        if not published_at_str:
            print("[WARN] published_at ausente. Usando timestamp atual.")
            published_at = datetime.now()
            target_item["published_at"] = published_at.isoformat()
        else:
            try:
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            except Exception:
                published_at = datetime.now()
                
        target_item["post_publish_tracking_status"] = "waiting_24h_metrics"
        target_item["published_tracking_started_at"] = datetime.now().isoformat()
        
        target_item["metrics_due_24h_at"] = (published_at + timedelta(hours=24)).isoformat()
        target_item["metrics_due_48h_at"] = (published_at + timedelta(hours=48)).isoformat()
        target_item["metrics_due_7d_at"] = (published_at + timedelta(days=7)).isoformat()
        target_item["updated_at"] = datetime.now().isoformat()
        
        self.history_repo.save(history)
        return {"status": "success", "message": "Acompanhamento iniciado."}

    def update_post_publish_tracking_status(self, item_id: str, tracking_status: str, confirm: bool = True) -> dict:
        if not confirm:
            return {"status": "error", "message": "Confirmação necessária."}
            
        valid_statuses = [
            "waiting_24h_metrics", "waiting_48h_metrics", "waiting_7d_metrics",
            "metrics_imported", "analysis_generated", "completed"
        ]
        
        if tracking_status not in valid_statuses:
            return {"status": "error", "message": "Status de acompanhamento inválido."}
            
        history = self.history_repo.load()
        target_item = None
        
        for entry in history:
            for item in entry.get("items", []):
                if self._get_item_identifier(item) == item_id:
                    target_item = item
                    break
            if target_item:
                break
                
        if not target_item:
            return {"status": "error", "message": "Item não encontrado."}
            
        if target_item.get("status") != "published":
            return {"status": "error", "message": "Item precisa estar publicado."}
            
        is_main, reason = self._is_main_publication(target_item)
        if not is_main and (target_item.get("status") == "used_as_asset" or target_item.get("linked_to_item_id") or target_item.get("asset_role")):
            return {"status": "error", "message": "Não é possível atualizar acompanhamento em asset vinculado."}
            
        from datetime import datetime
        target_item["post_publish_tracking_status"] = tracking_status
        target_item["updated_at"] = datetime.now().isoformat()
        
        if tracking_status == "completed":
            target_item["post_publish_completed_at"] = datetime.now().isoformat()
            
        self.history_repo.save(history)
        return {"status": "success", "message": "Status de acompanhamento atualizado."}

    def _validate_schedule_datetime(self, scheduled_date: str, scheduled_time: str, action: str) -> str:
        try:
            dt_str = f"{scheduled_date}T{scheduled_time}:00"
            dt_obj = DateTime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
            tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
            dt_aware = dt_obj.replace(tzinfo=tz)
            now_aware = DateTime.now(tz)

            if dt_aware < now_aware:
                raise ValueError(f"Data e hora de {action} não podem estar no passado.")
            return dt_str
        except Exception as e:
            if "passado" in str(e):
                raise ValueError(str(e))
            raise ValueError(f"Data ou horário inválido: {e}")

    def _is_asset(self, item: dict) -> bool:
        return (
            item.get("status") == "used_as_asset"
            or bool(item.get("linked_to_item_id"))
            or bool(item.get("asset_role"))
        )
