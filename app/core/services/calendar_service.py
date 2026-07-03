import os
from typing import List, Dict, Any

from app.core.repositories.history_repository import HistoryRepository

class CalendarService:
    def __init__(self, history_repo: HistoryRepository, llm_client):
        self.history_repo = history_repo
        self.llm_client = llm_client

    def get_editorial_calendar(self) -> list:
        """Retorna uma lista de peças publicáveis para a Agenda Editorial."""
        history = self.history_repo.load()
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
        history = self.history_repo.load()
        date_prefix = folder_id[:10]
        
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
            self.history_repo.save(history)
        else:
            print(f"[BrandOS] Item não encontrado para agendamento {folder_id} {item_id}")

    def add_metrics_snapshot(self, folder_id: str, item_id: str, snapshot_data: dict):
        history = self.history_repo.load()
        date_prefix = folder_id[:10]
        
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
            self.history_repo.save(history)
        else:
            raise Exception("Item não encontrado no publication-log.json")

    def generate_snapshot_analysis(self, folder_id: str, item_id: str, snapshot_data: dict) -> str:
        history = self.history_repo.load()
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
        try:
            analysis = self.llm_client.generate_content(system_prompt, user_prompt)
            return analysis.strip()
        except Exception as e:
            print(f"Erro no Gemini: {e}")
            raise e

    def import_linkedin_analytics(self, folder_id: str, item_id: str, file_path: str, original_filename: str) -> dict:
        import pandas as pd
        import shutil
        import json
        from datetime import datetime
        import re
        
        assets_dir = os.path.join(self.history_repo.base_dir, "data", "assets")
        
        # 1. Armazenar o arquivo em data/assets/{folder_id}-{item_id}/analytics/
        asset_folder_name = f"{folder_id}-{item_id}"
        analytics_dir = os.path.join(assets_dir, asset_folder_name, "analytics")
        os.makedirs(analytics_dir, exist_ok=True)
        
        # Sanitizar filename
        safe_filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', original_filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        final_filename = f"{timestamp}_{safe_filename}"
        
        dest_path = os.path.join(analytics_dir, final_filename)
        shutil.copy2(file_path, dest_path)
        
        # Atualizar manifest.json
        manifest_path = os.path.join(assets_dir, asset_folder_name, "manifest.json")
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
