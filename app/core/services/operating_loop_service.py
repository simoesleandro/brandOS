import os
from datetime import datetime, timezone

from app.core.repositories.history_repository import HistoryRepository


class OperatingLoopService:
    def __init__(self, base_dir: str, history_repo: HistoryRepository, briefing_service, cmo_service):
        self.base_dir = base_dir
        self.history_repo = history_repo
        self.briefing_service = briefing_service
        self.cmo_service = cmo_service

    def get_today_operating_loop(self) -> dict:
        history = self.history_repo.load()
        posts = self._main_posts(history)
        due_publications = self._due_publications(posts)
        due_metrics = self._due_metrics(posts)
        generated_posts = [p for p in posts if p.get("status") in ["generated", "edited", "draft"]]
        approved_briefings = self._approved_briefings_waiting_generation()
        latest_cmo = self._latest_cmo_recommendation()
        latest_learning = self._latest_editorial_learning(posts)

        secondary_actions = self._secondary_actions(
            due_publications=due_publications,
            due_metrics=due_metrics,
            generated_posts=generated_posts,
            approved_briefings=approved_briefings,
            latest_cmo=latest_cmo,
        )

        if due_publications:
            return self._response(
                "publish_due",
                "Há publicação agendada vencida ou para hoje.",
                due_publications[0],
                secondary_actions,
                due_publications,
                due_metrics,
                approved_briefings,
                latest_cmo,
                latest_learning,
            )

        if due_metrics:
            return self._response(
                "capture_metrics",
                "Há métricas pós-publicação para capturar agora.",
                due_metrics[0],
                secondary_actions,
                due_publications,
                due_metrics,
                approved_briefings,
                latest_cmo,
                latest_learning,
            )

        if generated_posts:
            return self._response(
                "review_generated",
                "Existem posts gerados aguardando revisão editorial.",
                generated_posts[0],
                secondary_actions,
                due_publications,
                due_metrics,
                approved_briefings,
                latest_cmo,
                latest_learning,
            )

        if approved_briefings:
            return self._response(
                "approve_briefing",
                "Há briefing aprovado esperando geração da semana.",
                approved_briefings[0],
                secondary_actions,
                due_publications,
                due_metrics,
                approved_briefings,
                latest_cmo,
                latest_learning,
            )

        if latest_cmo:
            return self._response(
                "create_next_briefing",
                "Existe recomendação do CMO pronta para virar briefing.",
                latest_cmo,
                secondary_actions,
                due_publications,
                due_metrics,
                approved_briefings,
                latest_cmo,
                latest_learning,
            )

        return self._response(
            "generate_cmo_recommendation",
            "Nenhuma recomendação ativa encontrada; comece pela estratégia da próxima semana.",
            None,
            secondary_actions,
            due_publications,
            due_metrics,
            approved_briefings,
            latest_cmo,
            latest_learning,
        )

    def _response(
        self,
        next_action: str,
        reason: str,
        primary_item,
        secondary_actions: list,
        due_publications: list,
        due_metrics: list,
        approved_briefings: list,
        latest_cmo: dict | None,
        latest_learning: dict | None,
    ) -> dict:
        warnings = []
        if not due_publications and not approved_briefings and not latest_cmo:
            warnings.append("Sem semana editorial pronta. O próximo ciclo deve começar pelo CMO.")

        return {
            "next_action": next_action,
            "reason": reason,
            "primary_item": primary_item,
            "secondary_actions": secondary_actions,
            "warnings": warnings,
            "due_publications": due_publications[:5],
            "due_metrics": due_metrics[:5],
            "approved_briefings": approved_briefings[:3],
            "last_cmo_recommendation": latest_cmo,
            "last_editorial_learning": latest_learning,
        }

    def _main_posts(self, history: list) -> list:
        posts = []
        for entry in history:
            folder_id = entry.get("id")
            for item in entry.get("items", []):
                if self._is_asset(item):
                    continue
                if item.get("type") not in [None, "", "post", "linkedin_post", "main_post", "publication", "main_publication"]:
                    continue
                enriched = dict(item)
                enriched["folder_id"] = folder_id
                enriched["url"] = f"/publications/{folder_id}/item/{item.get('item_id') or item.get('id')}"
                enriched["publish_url"] = f"/publish/post/{item.get('item_id') or item.get('id')}"
                posts.append(enriched)
        return posts

    def _due_publications(self, posts: list) -> list:
        now = datetime.now().astimezone()
        due = []
        for item in posts:
            if item.get("status") not in ["scheduled", "publishing_ready", "ready_to_publish"]:
                continue
            scheduled = self._parse_item_date(item, ["scheduled_at", "scheduled_date", "scheduled_for"])
            if scheduled is None or scheduled <= now:
                due.append(item)
        return sorted(due, key=lambda x: x.get("scheduled_at") or x.get("scheduled_date") or x.get("scheduled_for") or "")

    def _due_metrics(self, posts: list) -> list:
        now = datetime.now().astimezone()
        due = []
        for item in posts:
            if item.get("status") != "published":
                continue
            tracking = item.get("post_publish_tracking_status")
            if tracking in [None, "", "completed", "analysis_generated"]:
                continue
            due_at = self._metric_due_at(item, tracking)
            if due_at and due_at <= now:
                due.append(item)
        return sorted(due, key=lambda x: self._metric_due_at(x, x.get("post_publish_tracking_status")) or now)

    def _approved_briefings_waiting_generation(self) -> list:
        result = []
        for briefing in self.briefing_service.list_briefings():
            status = str(briefing.get("status", "")).strip().lower()
            if status in ["approved", "briefing_aprovado"] and not briefing.get("generated_folder"):
                item = dict(briefing)
                item["url"] = f"/briefings/{briefing.get('filename')}"
                result.append(item)
        return result

    def _latest_cmo_recommendation(self) -> dict | None:
        active, _, _ = self.cmo_service.list_recommendations()
        if not active:
            return None
        latest = dict(active[0])
        latest["url"] = f"/cmo/recommendations/{latest.get('id')}"
        return latest

    def _latest_editorial_learning(self, posts: list) -> dict | None:
        learned = [p for p in posts if p.get("editorial_learning_file") or p.get("editorial_learning_status") == "generated"]
        if not learned:
            return None
        learned.sort(key=lambda x: x.get("editorial_learning_generated_at") or x.get("updated_at") or "", reverse=True)
        latest = dict(learned[0])
        latest["learning_url"] = f"/publications/posts/{latest.get('item_id') or latest.get('id')}/learning"
        return latest

    def _secondary_actions(self, due_publications, due_metrics, generated_posts, approved_briefings, latest_cmo) -> list:
        actions = []
        if due_publications:
            actions.append({"label": "Abrir publicação", "url": due_publications[0].get("publish_url"), "kind": "publish_due"})
        if due_metrics:
            actions.append({"label": "Capturar métricas", "url": due_metrics[0].get("url"), "kind": "capture_metrics"})
        if generated_posts:
            actions.append({"label": "Revisar post gerado", "url": generated_posts[0].get("url"), "kind": "review_generated"})
        if approved_briefings:
            actions.append({"label": "Gerar semana do briefing", "url": approved_briefings[0].get("url"), "kind": "approve_briefing"})
        if latest_cmo:
            actions.append({"label": "Criar briefing da recomendação", "url": f"/cmo/recommendations/{latest_cmo.get('id')}", "kind": "create_next_briefing"})
        actions.append({"label": "Ver painel operacional", "url": "/ops", "kind": "ops"})
        return actions[:5]

    def _metric_due_at(self, item: dict, tracking_status: str):
        field_by_status = {
            "waiting_24h_metrics": "metrics_due_24h_at",
            "waiting_48h_metrics": "metrics_due_48h_at",
            "waiting_7d_metrics": "metrics_due_7d_at",
            "metrics_imported": "last_metrics_imported_at",
        }
        field = field_by_status.get(tracking_status)
        return self._parse_datetime(item.get(field)) if field else None

    def _parse_item_date(self, item: dict, fields: list[str]):
        for field in fields:
            value = item.get(field)
            parsed = self._parse_datetime(value)
            if parsed:
                return parsed
        return None

    def _parse_datetime(self, value):
        if not value:
            return None
        try:
            text = str(value)
            if len(text) == 10:
                text = f"{text}T23:59:59"
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.astimezone()
            return parsed
        except Exception:
            return None

    def _is_asset(self, item: dict) -> bool:
        return (
            item.get("status") == "used_as_asset"
            or bool(item.get("linked_to_item_id"))
            or bool(item.get("asset_role"))
        )
