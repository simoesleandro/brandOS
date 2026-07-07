import uuid
from datetime import datetime

from app.core.repositories.history_repository import HistoryRepository


class OpsService:
    def __init__(self, history_repo: HistoryRepository, base_dir: str = "."):
        self.history_repo = history_repo
        self.base_dir = base_dir

    def normalize_registry_item_ids(self) -> dict:
        history = self.history_repo.load()
        if not history:
            return {"normalized_count": 0, "normalized_items": [], "warnings": ["Histórico vazio."]}

        normalized_count = 0
        normalized_items = []
        warnings = []

        for _, item in self.history_repo.iter_items(history):
            if not item.get("item_id"):
                if item.get("id"):
                    item["item_id"] = item["id"]
                else:
                    short_uuid = str(uuid.uuid4())[:8]
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    item["item_id"] = f"item-{ts}-{short_uuid}"

                item["normalized_at"] = datetime.now().isoformat()
                item["normalized_by"] = "system"

                normalized_count += 1
                normalized_items.append(item["item_id"])

        if normalized_count > 0:
            self.history_repo.save(history)

        return {
            "normalized_count": normalized_count,
            "normalized_items": normalized_items,
            "warnings": warnings
        }

    def preview_invalid_items(self) -> dict:
        history = self.history_repo.load()
        suspects = []

        if not history:
            return {"suspects": suspects}

        for _, item in self.history_repo.iter_items(history):
            identifier = self.history_repo.get_item_identifier(item)
            title = item.get("title")

            reason = []
            if not identifier:
                reason.append("Sem identifier")
            if not title or str(title).strip() == "":
                reason.append("Título vazio")
            elif "test" in str(title).lower():
                reason.append("Contém 'Test' no título")

            sched = item.get("scheduled_at")
            if sched:
                try:
                    datetime.fromisoformat(sched)
                except ValueError:
                    reason.append("Data de agendamento inválida")

            if reason:
                suspects.append({
                    "identifier": identifier,
                    "title": title,
                    "status": item.get("status"),
                    "reasons": reason
                })

        return {"suspects": suspects}

    def discard_items_bulk(self, item_ids: list, reason: str, confirm: bool) -> dict:
        if not confirm:
            raise ValueError("Confirmação obrigatória.")

        history = self.history_repo.load()
        if not history:
            raise ValueError("Histórico vazio.")

        discarded_count = 0
        now_str = datetime.now().isoformat()

        for _, item in self.history_repo.iter_items(history):
            identifier = self.history_repo.get_item_identifier(item)
            if identifier in item_ids:
                status = item.get("status")
                if status == "published":
                    continue
                if status == "used_as_asset" or item.get("linked_to_item_id") or item.get("asset_role"):
                    continue

                item["status"] = "discarded"
                item.setdefault("discard_history", []).append({
                    "discarded_at": now_str,
                    "reason": reason,
                    "previous_status": status
                })

                for field in ["scheduled_at", "scheduled_date", "scheduled_time", "scheduled_for"]:
                    item.pop(field, None)

                discarded_count += 1

        if discarded_count > 0:
            self.history_repo.save(history)

        return {"discarded_count": discarded_count}
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

    def get_dashboard_metrics(self):
        history = self.history_repo.load()
        
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
            project_added = False
            for item in entry.get("items", []):
                status = item.get("status")
                
                is_main, reason = self._is_main_publication(item)
                
                if not is_main:
                    # Check if it's a linked asset
                    if status == "used_as_asset" or item.get("linked_to_item_id") or item.get("asset_role"):
                        linked_assets_items += 1
                        if entry.get("project") and entry.get("project") != "Desconhecido":
                            active_projects.add(entry.get("project"))
                    continue
                    
                # It's a main publication
                if entry.get("project") and entry.get("project") != "Desconhecido":
                    active_projects.add(entry.get("project"))
                    
                total_items += 1

                folder_id = entry.get("id") or f"{entry.get('date')}-semana-brandos"
                
                if status == "ready_to_publish":
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

    def get_ops_dashboard(self) -> dict:
        import os, json
        from datetime import datetime, timedelta
        import zoneinfo
        
        log_path = os.path.join(self.base_dir, "data", "registry", "publication-log.json")
        
        counts = {
            "total_main_posts": 0,
            "draft_count": 0,
            "generated_count": 0,
            "edited_count": 0,
            "approved_count": 0,
            "scheduled_count": 0,
            "publishing_ready_count": 0,
            "published_count": 0,
            "discarded_count": 0,
            "pending_count": 0,
            "without_date_count": 0,
            "overdue_count": 0,
            "ready_to_schedule_count": 0,
            "scheduled_next_7_days_count": 0,
            "waiting_metrics_count": 0,
            "metrics_imported_count": 0,
            "analysis_generated_count": 0,
            "completed_count": 0,
            "learnings_generated_count": 0
        }
        
        pipeline_groups = {
            "draft": [],
            "generated": [],
            "edited": [],
            "approved": [],
            "scheduled": [],
            "publishing_ready": [],
            "published": [],
            "discarded": []
        }
        
        lists = {
            "next_7_days": [],
            "ready_to_schedule": [],
            "pending_reviews": [],
            "overdue": [],
            "warnings": [],
            "ignored_items": []
        }
        
        post_publish_groups = {
            "waiting_24h_metrics": [],
            "waiting_48h_metrics": [],
            "waiting_7d_metrics": [],
            "metrics_imported": [],
            "analysis_generated": [],
            "completed": []
        }
        
        history = self.history_repo.load()
        if not history:
            return {"counts": counts, "pipeline_groups": pipeline_groups, "lists": lists, "error": "publication-log.json vazio ou não encontrado."}
                
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_aware = datetime.now(tz)
        today_str = now_aware.strftime("%Y-%m-%d")
        next_7_days = [(now_aware + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(8)]
        
        for entry in history:
            # support loose items at the root of history
            items_to_process = entry.get("items", []) if "items" in entry else [entry]
            for item in items_to_process:
                identifier = self._get_item_identifier(item)
                item["identifier"] = identifier
                
                # Main publication filter Phase 5.2 update
                is_main, reason = self._is_main_publication(item)
                if not is_main:
                    lists["ignored_items"].append({"item": item, "reason": reason})
                    continue
                    
                if not identifier:
                    lists["warnings"].append({"message": "Item sem identificador detectado. Ações desabilitadas até normalização.", "item": item})
                    
                counts["total_main_posts"] += 1
                status = item.get("status", "unknown")
                
                # Treat missing status as draft
                if not item.get("status"):
                    status = "draft"
                    item["status"] = "draft"
                    item["_missing_status"] = True # purely for visual cues if needed
                    
                # Basic status counts
                if status == "draft": counts["draft_count"] += 1
                elif status == "generated": counts["generated_count"] += 1
                elif status == "edited": counts["edited_count"] += 1
                elif status == "approved": counts["approved_count"] += 1
                elif status == "scheduled": counts["scheduled_count"] += 1
                elif status == "publishing_ready": counts["publishing_ready_count"] += 1
                elif status == "published": counts["published_count"] += 1
                elif status == "discarded": counts["discarded_count"] += 1
                
                if status in ["draft", "generated", "edited"]:
                    counts["pending_count"] += 1
                    lists["pending_reviews"].append(item)
                    
                # Date logic
                sched_at = item.get("scheduled_at")
                sched_date = item.get("scheduled_date")
                sched_time = item.get("scheduled_time")
                sched_for = item.get("scheduled_for")
                pub_at = item.get("published_at")
                
                # Post-publication tracking logic
                if status == "published":
                    tracking_status = item.get("post_publish_tracking_status")
                    if tracking_status:
                        if tracking_status in post_publish_groups:
                            post_publish_groups[tracking_status].append(item)
                            
                        if tracking_status in ["waiting_24h_metrics", "waiting_48h_metrics", "waiting_7d_metrics"]:
                            counts["waiting_metrics_count"] += 1
                        elif tracking_status == "metrics_imported":
                            counts["metrics_imported_count"] += 1
                        elif tracking_status == "analysis_generated":
                            counts["analysis_generated_count"] += 1
                        elif tracking_status == "completed":
                            counts["completed_count"] += 1

                # Pipeline population
                if status in pipeline_groups:
                    pipeline_groups[status].append(item)
                    

                # Pós-publicação: Aprendizado Editorial
                if item.get("editorial_learning_file") or item.get("editorial_learning_status") == "generated":
                    counts["learnings_generated_count"] += 1

                # Without date
                if not sched_at and not sched_date and not sched_for and not pub_at and status != "discarded":
                    counts["without_date_count"] += 1
                    
                # Ready to schedule
                if status == "approved" and not sched_at and not sched_date:
                    counts["ready_to_schedule_count"] += 1
                    lists["ready_to_schedule"].append(item)
                    
                # Resolve unified date string for calculations
                target_date_str = None
                target_dt_aware = None
                
                if sched_at:
                    target_date_str = sched_at[:10]
                    try:
                        dt_obj = datetime.fromisoformat(sched_at)
                        target_dt_aware = dt_obj if dt_obj.tzinfo else dt_obj.replace(tzinfo=tz)
                    except ValueError:
                        ident = self._get_item_identifier(item) or "desconhecido"
                        lists["warnings"].append({"message": f"Item {ident} possui data de agendamento inválida: {sched_at}.", "item": item})
                elif sched_date:
                    target_date_str = sched_date
                    try:
                        t_str = sched_time if sched_time else "00:00"
                        dt_obj = datetime.strptime(f"{sched_date}T{t_str[:5]}:00", "%Y-%m-%dT%H:%M:%S")
                        target_dt_aware = dt_obj.replace(tzinfo=tz)
                    except ValueError:
                        ident = self._get_item_identifier(item) or "desconhecido"
                        lists["warnings"].append({"message": f"Item {ident} possui data de agendamento inválida: {sched_date}.", "item": item})
                        
                if status in ["scheduled", "publishing_ready"] and target_dt_aware:
                    if target_dt_aware < now_aware and not pub_at and status != "published":
                        counts["overdue_count"] += 1
                        lists["overdue"].append(item)
                    elif target_date_str in next_7_days:
                        counts["scheduled_next_7_days_count"] += 1
                        lists["next_7_days"].append(item)
                        
        return {
            "counts": counts,
            "pipeline_groups": pipeline_groups,
            "lists": lists,
            "error": None
        }
