import os
import re
import json
from datetime import datetime
from app.workflows.weekly_workflow import run_weekly_workflow
from app.core.repositories.history_repository import HistoryRepository
from app.core.services.asset_service import AssetService

class BrandOSService:
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.registry_dir = os.path.join(self.base_dir, "data", "registry")
        self.knowledge_dir = os.path.join(self.base_dir, "data", "knowledge")
        self.inbox_dir = os.path.join(self.base_dir, "data", "inbox")
        self.generated_dir = os.path.join(self.base_dir, "data", "generated")
        self.assets_dir = os.path.join(self.base_dir, "data", "assets")
        os.makedirs(self.assets_dir, exist_ok=True)
        self.history_repo = HistoryRepository(base_dir)
        self.asset_service = AssetService(self.assets_dir, self.history_repo)
        from app.core.llm_client import LLMClient
        self.llm = LLMClient()
            
        from app.core.services.calendar_service import CalendarService
        self.calendar_service = CalendarService(self.history_repo, self.llm)
        
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
        if not re.search(r'^\s*Status:\s*(briefing_aprovado|approved)\s*$', briefing_content, re.IGNORECASE | re.MULTILINE):
            raise ValueError("Este briefing ainda não está aprovado para geração de semana editorial.")
            
        # 2. Validate date format (YYYY-MM-DD)
        data_inicial_str = options.get('start_date', '')

        # Extrair metadata CMO
        is_cmo = False
        source_rec_id = None
        if re.search(r'Fonte:\s*CMO Recommendation', briefing_content, re.IGNORECASE) or re.search(r'Origem técnica:\s*cmo_recommendation', briefing_content, re.IGNORECASE):
            is_cmo = True
            rec_match = re.search(r'Recommendation ID:\s*(.*)', briefing_content, re.IGNORECASE)
            if rec_match:
                source_rec_id = rec_match.group(1).strip()
    
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
        try:
            response_text = self.llm.generate_content("Você é o Content Strategist e Copywriter do BrandOS.", prompt)
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
        import re
        import unicodedata
        def local_slugify(value):
            value = str(value)
            value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
            value = re.sub(r'[^\w\s-]', '', value.lower())
            return re.sub(r'[-\s]+', '-', value).strip('-_')
        
        now = datetime.datetime.now()
        timestamp = now.strftime("%H%M")
        data_inicial = data_inicial_str
        slug = local_slugify(options.get('project_slug', 'projeto'))
        
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
        log_data = []
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
                    if not isinstance(log_data, list):
                        log_data = []
            except Exception as e:
                print(f"[CMO] Erro ao carregar publication-log.json: {e}")
                log_data = []
            
        # Helper to parse initial date and add days for suggested_for
        from datetime import datetime, timedelta
        dt = datetime.strptime(data_inicial_str, "%Y-%m-%d")
            
        data_seg = dt.strftime("%Y-%m-%d")
        data_qua = (dt + timedelta(days=2)).strftime("%Y-%m-%d")
        data_sex = (dt + timedelta(days=4)).strftime("%Y-%m-%d")
        
        # Adicionar apenas posts principais
        new_items = [
            {
                "id": f"post-segunda-{timestamp}",
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
                "planned_day": "segunda",
                "generated_folder": folder_name
            },
            {
                "id": f"post-quarta-{timestamp}",
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
                "planned_day": "quarta",
                "generated_folder": folder_name
            },
            {
                "id": f"post-sexta-{timestamp}",
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
                "planned_day": "sexta",
                "generated_folder": folder_name
            }
        ]
        for item in new_items:
            if is_cmo:
                item["source"] = "generated_from_cmo_briefing"
                item["source_briefing_file"] = filename
                if source_rec_id:
                    item["source_recommendation_id"] = source_rec_id
                item["generated_folder"] = folder_name
                item["generated_from_cmo"] = True
                
        new_week = {
            "id": folder_name,
            "date": data_inicial_str,
            "project": options.get('project_slug', 'Projeto Desconhecido'),
            "theme": blocks.get("PLANO EDITORIAL", "").split("\\n")[0][:100],
            "status": "generated",
            "items": new_items
        }
        
        log_data.append(new_week)
        
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
            
        # 4. Atualizar briefing
        try:
            briefing_path = os.path.join(self.generated_dir, "briefings", filename)
            if os.path.exists(briefing_path):
                with open(briefing_path, "r", encoding="utf-8") as f:
                    b_content = f.read()
                import re
                b_content = re.sub(r'^Status:\s*(.*)$', 'Status: generated', b_content, flags=re.MULTILINE | re.IGNORECASE)
                b_content += "\n\n---\n\n*Semana gerada em: " + now.isoformat() + "*"
                with open(briefing_path, "w", encoding="utf-8") as f:
                    f.write(b_content)
        except Exception as e:
            print(f"[CMO] Erro ao atualizar status do briefing: {e}")
            
        print("[CMO] Semana gerada com sucesso.")
        return {"status": "success", "folder": folder_name}


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
        log_path = os.path.join(self.base_dir, "data", "registry", "publication-log.json")
        log_items = []
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
                    log_items = log_data.get("items", [])
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
        import zoneinfo
        from datetime import datetime
        if not confirm:
            raise ValueError("É necessário confirmar o descarte.")
            
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
            raise ValueError(f"Post {item_id} não encontrado.")
            
        if target.get("status") == "published":
            raise ValueError("Posts já publicados não podem ser descartados por este fluxo.")
            
        if target.get("status") == "used_as_asset" or target.get("linked_to_item_id") or target.get("asset_role"):
            raise ValueError("Assets vinculados não podem ser descartados como publicações principais.")
            
        if target.get("status") not in ["draft", "generated", "edited", "approved", "scheduled", "publishing_ready", None, ""]:
            raise ValueError(f"O status '{target.get('status')}' não permite descarte.")
            
        old_status = target.get("status")
        
        target["status"] = "discarded"
        target["discarded_from_status"] = old_status
        
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_aware = datetime.now(tz)
        target["discarded_at"] = now_aware.strftime("%Y-%m-%dT%H:%M:%S%z")
        target["discarded_by"] = "human"
        target["discard_reason"] = reason
        target["updated_at"] = target["discarded_at"]
        
        # Clear operational scheduling fields
        for field in ["scheduled_at", "scheduled_date", "scheduled_time", "scheduled_for", "priority"]:
            if field in target:
                del target[field]
                
        if "discard_history" not in target:
            target["discard_history"] = []
            
        target["discard_history"].append({
            "event": "discarded",
            "from_status": old_status,
            "to_status": "discarded",
            "discarded_at": target["discarded_at"],
            "discarded_by": target["discarded_by"],
            "reason": reason
        })
        
        self.history_repo.save(history)
        
        return {
            "status": "success",
            "message": "Post descartado com sucesso."
        }

    def update_item_content(self, item_id: str, content: str, source_note: str = "") -> dict:
        import os, shutil, datetime
        
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
            raise ValueError(f"Item {item_id} não encontrado no histórico.")
            
        status = target_item.get("status", "")
        
        # Validation rules
        if status == "published":
            raise ValueError("Posts já publicados não podem ser editados por este fluxo. Crie uma nova versão ou use uma revisão futura.")
            
        if status == "used_as_asset" or target_item.get("linked_to_item_id") or target_item.get("asset_role"):
            raise ValueError("Assets vinculados não podem ser editados como publicações principais.")
            
        if not content or not content.strip():
            raise ValueError("Conteúdo não pode estar vazio.")
            
        content_file = target_item.get("content_file")
        if not content_file:
            raise ValueError("Item não possui arquivo de conteúdo associado.")
            
        # Resolve full path
        file_path = os.path.join(self.base_dir, content_file)
        if not os.path.exists(file_path):
            raise ValueError(f"Arquivo {content_file} não encontrado fisicamente.")
            
        # Create backup
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d-%H%M%S")
        
        # Determine backup dir
        generated_folder = target_item.get("generated_folder")
        if generated_folder:
            backups_dir = os.path.join(self.base_dir, "data", "generated", generated_folder, "backups")
        else:
            file_dir = os.path.dirname(file_path)
            backups_dir = os.path.join(file_dir, "backups")
            
        os.makedirs(backups_dir, exist_ok=True)
        filename = os.path.basename(file_path)
        backup_file = os.path.join(backups_dir, f"{filename.replace('.md', '')}-{timestamp}.md")
        
        try:
            shutil.copy2(file_path, backup_file)
        except Exception as e:
            raise ValueError(f"Erro ao criar backup do markdown: {e}")
            
        # Overwrite content
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise ValueError(f"Erro ao salvar o conteúdo editado: {e}")
            
        # Update metadata
        target_item["content_version"] = "manual_final"
        target_item["content_source"] = "human_refined"
        target_item["updated_at"] = now.isoformat()
        target_item["last_edited_at"] = now.isoformat()
        target_item["edited_by"] = "human"
        target_item["editorial_source"] = "manual_edit"
        
        if status == "generated":
            target_item["status"] = "edited"
            
        # Update editorial history
        if "editorial_history" not in target_item:
            target_item["editorial_history"] = []
            
        note = source_note if source_note else "Texto refinado manualmente no BrandOS."
            
        target_item["editorial_history"].append({
            "event": "content_edited",
            "edited_at": now.isoformat(),
            "edited_by": "human",
            "source": "manual_edit",
            "backup_file": os.path.relpath(backup_file, self.base_dir).replace("\\", "/"),
            "note": note
        })
        
        # Save to repo (atomic + registry backup already implemented in save)
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
        import os, shutil, datetime, tempfile, json
        
        folder_name = os.path.basename(folder_name)
        if planned_day not in ["segunda", "quarta", "sexta"]:
            raise ValueError("Dia inválido. Use 'segunda', 'quarta' ou 'sexta'.")
            
        log_path = os.path.join(self.base_dir, "data", "registry", "publication-log.json")
        if not os.path.exists(log_path):
            raise ValueError("publication-log.json não encontrado.")
            
        # Load registry
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                log_data = json.load(f)
        except Exception as e:
            raise ValueError(f"Erro ao ler registry: {e}")
            
        item_found = False
        target_item = None
        for item in log_data:
            if item.get("source") == "generated_from_briefing" and item.get("generated_folder") == folder_name and item.get("planned_day") == planned_day:
                target_item = item
                item_found = True
                break
                
        if not item_found:
            raise ValueError("Post não encontrado no registry.")
            
        if target_item.get("status") == "approved":
            return {"status": "success", "message": "Post já estava aprovado."}
            
        if target_item.get("status") not in ["generated", "edited"]:
            raise ValueError(f"Status '{target_item.get('status')}' não permite aprovação.")
            
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d-%H%M%S")
        
        # Backup registry
        reg_backups_dir = os.path.join(self.base_dir, "data", "registry", "backups")
        os.makedirs(reg_backups_dir, exist_ok=True)
        reg_backup_file = os.path.join(reg_backups_dir, f"publication-log-{timestamp}.json")
        try:
            shutil.copy2(log_path, reg_backup_file)
        except Exception as e:
            raise ValueError(f"Erro ao criar backup do publication-log.json: {e}")
            
        target_item["status"] = "approved"
        target_item["updated_at"] = now.isoformat()
        if "approved_at" not in target_item:
            target_item["approved_at"] = now.isoformat()
            
        # Save safe
        try:
            temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(log_path), text=True)
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, log_path)
        except Exception as e:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            raise ValueError(f"Erro ao atualizar publication-log.json: {e}")
            
        return {"status": "success", "message": "Post aprovado com sucesso."}
    
    def approve_generated_week(self, folder_name: str) -> dict:
        import os, shutil, datetime, tempfile, json
        
        folder_name = os.path.basename(folder_name)
        log_path = os.path.join(self.base_dir, "data", "registry", "publication-log.json")
        if not os.path.exists(log_path):
            raise ValueError("publication-log.json não encontrado.")
            
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                log_data = json.load(f)
        except Exception as e:
            raise ValueError(f"Erro ao ler registry: {e}")
            
        items_to_approve = []
        for item in log_data:
            if item.get("source") == "generated_from_briefing" and item.get("generated_folder") == folder_name and item.get("planned_day") in ["segunda", "quarta", "sexta"]:
                items_to_approve.append(item)
                
        if not items_to_approve:
            raise ValueError("Nenhum post principal encontrado para esta semana.")
            
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d-%H%M%S")
        
        # Backup registry
        reg_backups_dir = os.path.join(self.base_dir, "data", "registry", "backups")
        os.makedirs(reg_backups_dir, exist_ok=True)
        reg_backup_file = os.path.join(reg_backups_dir, f"publication-log-{timestamp}.json")
        try:
            shutil.copy2(log_path, reg_backup_file)
        except Exception as e:
            raise ValueError(f"Erro ao criar backup do publication-log.json: {e}")
            
        updated = False
        for item in items_to_approve:
            if item.get("status") in ["generated", "edited"]:
                item["status"] = "approved"
                item["updated_at"] = now.isoformat()
                if "approved_at" not in item:
                    item["approved_at"] = now.isoformat()
                updated = True
                
        if updated:
            try:
                temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(log_path), text=True)
                with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                    json.dump(log_data, f, indent=2, ensure_ascii=False)
                os.replace(temp_path, log_path)
            except Exception as e:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
                raise ValueError(f"Erro ao salvar publication-log.json: {e}")
                
        return {"status": "success", "message": "Semana aprovada com sucesso."}
    

    def _is_asset(self, item: dict) -> bool:
        return (item.get("status") == "used_as_asset" or 
                bool(item.get("linked_to_item_id")) or 
                bool(item.get("asset_role")))
                
    def schedule_post(self, item_id: str, scheduled_date: str, scheduled_time: str, confirm: bool) -> dict:
        import os, shutil, tempfile, json
        from datetime import datetime
        import zoneinfo
        
        if not confirm:
            raise ValueError("Confirmação necessária.")
            
        try:
            dt_str = f"{scheduled_date}T{scheduled_time}:00"
            dt_obj = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
            tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
            dt_aware = dt_obj.replace(tzinfo=tz)
            now_aware = datetime.now(tz)
            
            if dt_aware < now_aware:
                raise ValueError("Data e hora de agendamento não podem estar no passado.")
        except Exception as e:
            if "passado" in str(e):
                raise ValueError(str(e))
            raise ValueError(f"Data ou horário inválido: {e}")
            
        log_path = os.path.join(self.base_dir, "data", "registry", "publication-log.json")
        if not os.path.exists(log_path):
            raise ValueError("Registry não encontrado.")
            
        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)
            
        target_item = None
        for item in log_data:
            if self._get_item_identifier(item) == item_id:
                target_item = item
                break
                
        if not target_item:
            raise ValueError("Post não encontrado.")
            
        if self._is_asset(target_item):
            raise ValueError("Assets vinculados não podem ser agendados como publicações principais.")
            
        if target_item.get("status") == "scheduled":
            raise ValueError("Post já está agendado. Use a rota de reagendamento.")
            
        if target_item.get("status") != "approved":
            raise ValueError(f"Post possui status '{target_item.get('status')}'. É necessário estar 'approved' para agendar.")
            
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d-%H%M%S")
        
        reg_backups_dir = os.path.join(self.base_dir, "data", "registry", "backups")
        os.makedirs(reg_backups_dir, exist_ok=True)
        reg_backup_file = os.path.join(reg_backups_dir, f"publication-log-{timestamp}.json")
        try:
            shutil.copy2(log_path, reg_backup_file)
        except Exception as e:
            raise ValueError(f"Erro ao criar backup do registry: {e}")
            
        target_item["status"] = "scheduled"
        target_item["scheduled_at"] = dt_str
        target_item["scheduled_date"] = scheduled_date
        target_item["scheduled_time"] = scheduled_time
        target_item["timezone"] = "America/Sao_Paulo"
        target_item["scheduled_by"] = "human"
        target_item["scheduled_source"] = "brandos_calendar"
        target_item["scheduled_at_created_at"] = now.isoformat()
        target_item["updated_at"] = now.isoformat()
        
        try:
            temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(log_path), text=True)
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, log_path)
        except Exception as e:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            raise ValueError(f"Erro ao salvar publication-log.json: {e}")
            
        return {"status": "success", "message": "Post agendado com sucesso."}
        
    def reschedule_post(self, item_id: str, scheduled_date: str, scheduled_time: str, confirm: bool) -> dict:
        import os, shutil, tempfile, json
        from datetime import datetime
        import zoneinfo
        
        if not confirm:
            raise ValueError("Confirmação necessária.")
            
        try:
            dt_str = f"{scheduled_date}T{scheduled_time}:00"
            dt_obj = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
            tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
            dt_aware = dt_obj.replace(tzinfo=tz)
            now_aware = datetime.now(tz)
            
            if dt_aware < now_aware:
                raise ValueError("Data e hora de reagendamento não podem estar no passado.")
        except Exception as e:
            if "passado" in str(e):
                raise ValueError(str(e))
            raise ValueError(f"Data ou horário inválido: {e}")
            
        log_path = os.path.join(self.base_dir, "data", "registry", "publication-log.json")
        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)
            
        target_item = None
        for item in log_data:
            if self._get_item_identifier(item) == item_id:
                target_item = item
                break
                
        if not target_item:
            raise ValueError("Post não encontrado.")
            
        if self._is_asset(target_item):
            raise ValueError("Assets vinculados não podem ser reagendados como publicações principais.")
            
        if target_item.get("status") != "scheduled":
            raise ValueError(f"Post possui status '{target_item.get('status')}'. É necessário estar 'scheduled' para reagendar.")
            
        if target_item.get("scheduled_date") == scheduled_date and target_item.get("scheduled_time") == scheduled_time:
            return {"status": "success", "message": "A data e horário são os mesmos, nenhuma alteração necessária."}
            
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d-%H%M%S")
        
        reg_backups_dir = os.path.join(self.base_dir, "data", "registry", "backups")
        os.makedirs(reg_backups_dir, exist_ok=True)
        reg_backup_file = os.path.join(reg_backups_dir, f"publication-log-{timestamp}.json")
        try:
            shutil.copy2(log_path, reg_backup_file)
        except Exception as e:
            raise ValueError(f"Erro ao criar backup do registry: {e}")
            
        target_item["scheduled_at"] = dt_str
        target_item["scheduled_date"] = scheduled_date
        target_item["scheduled_time"] = scheduled_time
        target_item["updated_at"] = now.isoformat()
        target_item["rescheduled_at"] = now.isoformat()
        target_item["rescheduled_by"] = "human"
        
        try:
            temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(log_path), text=True)
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, log_path)
        except Exception as e:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            raise ValueError(f"Erro ao salvar publication-log.json: {e}")
            
        return {"status": "success", "message": "Post reagendado com sucesso."}
        
    def unschedule_post(self, item_id: str, confirm: bool) -> dict:
        import os, shutil, tempfile, json
        from datetime import datetime
        
        if not confirm:
            raise ValueError("Confirmação necessária.")
            
        log_path = os.path.join(self.base_dir, "data", "registry", "publication-log.json")
        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)
            
        target_item = None
        for item in log_data:
            if self._get_item_identifier(item) == item_id:
                target_item = item
                break
                
        if not target_item:
            raise ValueError("Post não encontrado.")
            
        if self._is_asset(target_item):
            raise ValueError("Assets vinculados não podem ser manipulados como publicações principais.")
            
        if target_item.get("status") != "scheduled":
            raise ValueError(f"Post não está agendado (status atual: {target_item.get('status')}).")
            
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d-%H%M%S")
        
        reg_backups_dir = os.path.join(self.base_dir, "data", "registry", "backups")
        os.makedirs(reg_backups_dir, exist_ok=True)
        reg_backup_file = os.path.join(reg_backups_dir, f"publication-log-{timestamp}.json")
        try:
            shutil.copy2(log_path, reg_backup_file)
        except Exception as e:
            raise ValueError(f"Erro ao criar backup do registry: {e}")
            
        target_item["status"] = "approved"
        
        for key in ["scheduled_at", "scheduled_date", "scheduled_time"]:
            if key in target_item:
                del target_item[key]
                
        target_item["unscheduled_at"] = now.isoformat()
        target_item["unscheduled_by"] = "human"
        target_item["updated_at"] = now.isoformat()
        
        try:
            temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(log_path), text=True)
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, log_path)
        except Exception as e:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            raise ValueError(f"Erro ao salvar publication-log.json: {e}")
            
        return {"status": "success", "message": "Agendamento removido com sucesso."}
    



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
        import os
        import re
        import datetime
        import zoneinfo
        
        if not confirm:
            return {"status": "error", "message": "Confirmação necessária."}
            
        history = self.history_repo.load()
        if not history:
            return {"status": "error", "message": "Registry vazio."}
            
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
            
        if not self._is_main_publication(target_item):
            return {"status": "error", "message": "Não é possível gerar aprendizado para este tipo de item (asset/técnico)."}
            
        if target_item.get("status") != "published":
            return {"status": "error", "message": "Item precisa estar publicado para gerar aprendizado."}
            
        # Preparar pasta
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        learning_dir = os.path.join(base_dir, "data", "generated", "editorial-learning")
        os.makedirs(learning_dir, exist_ok=True)
        
        # Coletar contexto
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now = datetime.datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")
        date_str = datetime.datetime.now(tz).strftime("%Y-%m-%d")
        timestamp_str = datetime.datetime.now(tz).strftime("%Y%m%d-%H%M%S")
        
        safe_item_id = re.sub(r'[^a-zA-Z0-9-]', '-', item_id)
        filename = f"{date_str}-learning-{safe_item_id}-{timestamp_str}.md"
        filepath = os.path.join(learning_dir, filename)
        rel_filepath = os.path.join("data", "generated", "editorial-learning", filename).replace("\\", "/")
        
        title = target_item.get("title", "Sem título")
        published_at = target_item.get("published_at", "Não informada")
        published_url = target_item.get("published_url", "Não informada")
        format_info = target_item.get("format", "Não informado")
        
        # Conteúdo do post
        post_content = "Não encontrado"
        content_file = target_item.get("content_file")
        if content_file:
            abs_content = os.path.join(base_dir, content_file.replace("/", os.sep))
            if os.path.exists(abs_content):
                with open(abs_content, "r", encoding="utf-8") as f:
                    post_content = f.read()
                    
        # Métricas
        metrics = target_item.get("metrics", {})
        latest_metrics = metrics.get("latest", {})
        
        # Análise anterior
        analysis_content = "Não existe"
        analysis_file = target_item.get("post_publish_analysis_file")
        if analysis_file:
            abs_analysis = os.path.join(base_dir, analysis_file.replace("/", os.sep))
            if os.path.exists(abs_analysis):
                with open(abs_analysis, "r", encoding="utf-8") as f:
                    analysis_content = f.read()
                    
        prompt = f"""Você é o Editorial Learning Agent do BrandOS.

Sua tarefa é transformar uma publicação já publicada e seus dados disponíveis em aprendizado editorial reutilizável.

Não invente métricas.
Não assuma resultados que não estão nos dados.
Se faltarem métricas, diga claramente que a análise é limitada.

### DADOS DA PUBLICAÇÃO
Título: {title}
Formato: {format_info}
Publicado em: {published_at}
URL: {published_url}

### CONTEÚDO
{post_content}

### MÉTRICAS DISPONÍVEIS
{latest_metrics if latest_metrics else 'Nenhuma métrica encontrada.'}

### ANÁLISE QUALITATIVA ANTERIOR
{analysis_content}

### NOTAS DO USUÁRIO
{notes if notes else 'Nenhuma nota fornecida.'}

Gere um relatório em markdown com estas exatas seções:

# Aprendizado Editorial

## 1. Resumo da publicação
- título
- data de publicação
- status
- URL, se houver
- formato percebido

## 2. Tema e posicionamento
- tema central
- mensagem principal
- pilar de conteúdo
- conexão com marca pessoal

## 3. Leitura das métricas disponíveis
- métricas encontradas
- sinais positivos
- sinais fracos
- limitações da análise

Se não houver métricas, escreva EXATAMENTE a seguinte frase nesta seção:
"Ainda não há métricas suficientes importadas para concluir desempenho."

## 4. Avaliação editorial
- força do gancho
- clareza da mensagem
- profundidade
- especificidade
- risco de parecer genérico
- potencial de conversa

## 5. O que funcionou
Lista objetiva.

## 6. O que pode melhorar
Lista objetiva.

## 7. Recomendação para próximos posts
- repetir tema?
- repetir formato?
- transformar em carrossel?
- aprofundar tecnicamente?
- trazer bastidores?
- propor sequência?

## 8. Sugestões de próximos conteúdos
Gerar 3 a 5 ideias de posts futuros baseadas neste aprendizado.

## 9. Recomendação para o CMO Agent
Escrever um bloco curto que possa ser usado no planejamento da próxima semana.

Regras do texto:
- português do Brasil
- direto
- estratégico
- sem inventar números
- sem afirmar causalidade sem dados
- separar claramente opinião editorial de dado observado
"""
        
        try:
            markdown_content = self.llm.generate_content("Você é o Editorial Learning Agent do BrandOS, especialista em marketing.", prompt)
        except Exception as e:
            return {"status": "error", "message": f"Erro ao gerar aprendizado no LLM: {str(e)}"}
            
        # Salvar arquivo
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        # Atualizar JSON
        target_item["editorial_learning_status"] = "generated"
        target_item["editorial_learning_file"] = rel_filepath
        target_item["editorial_learning_generated_at"] = now
        target_item["updated_at"] = now
        if notes:
            target_item["notes_provided"] = True
            
        history_list = target_item.get("editorial_learning_history", [])
        history_list.append({
            "event": "learning_generated",
            "generated_at": now,
            "file": rel_filepath,
            "source": "manual_trigger"
        })
        target_item["editorial_learning_history"] = history_list
        
        self.history_repo.save(history)
        
        return {
            "status": "success",
            "learning_file": rel_filepath,
            "item_id": item_id,
            "generated_at": now
        }


    def get_latest_strategic_memory(self) -> dict:
        import os, json
        
        mem_dir = os.path.join(self.base_dir, "data", "generated", "strategic-memory")
        index_path = os.path.join(mem_dir, "index.json")
        
        if not os.path.exists(index_path):
            return None
            
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None
            
        memories = data.get("memories", [])
        if not memories:
            return None
            
        # Ordenar por data de geracao descendente
        memories.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
        latest = memories[0]
        
        # Ler o arquivo correspondente
        file_path = latest.get("file")
        if file_path:
            abs_path = os.path.join(self.base_dir, file_path.replace("/", os.sep))
            if os.path.exists(abs_path):
                with open(abs_path, "r", encoding="utf-8") as f:
                    latest["content"] = f.read()
            else:
                latest["content"] = "Arquivo não encontrado no sistema."
        else:
            latest["content"] = "Nenhum arquivo especificado."
            
        return latest

    def generate_strategic_memory(self, confirm: bool = True, window_days: int = 30, notes: str = None) -> dict:
        import os, json, tempfile, shutil
        import datetime
        import zoneinfo
        
        if not confirm:
            return {"status": "error", "message": "Confirmação necessária."}
            
        if not isinstance(window_days, int) or window_days < 7 or window_days > 180:
            return {"status": "error", "message": "O parâmetro window_days deve ser um número inteiro entre 7 e 180."}
            
        # Ler publication-log de forma segura, SOMENTE LEITURA
        # NUNCA usar self.history_repo.save()
        history = self.history_repo.load()
        if not history:
            return {"status": "error", "message": "Registry vazio."}
            
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_aware = datetime.datetime.now(tz)
        cutoff_date = now_aware - datetime.timedelta(days=window_days)
        
        qualified_posts = []
        
        for entry in history:
            for item in entry.get("items", []):
                if item.get("status") != "published":
                    continue
                    
                is_main, _ = self._is_main_publication(item)
                if not is_main:
                    continue
                    
                # Excluir explicitamente itens técnicos apenas por garantia (is_main deve pegar isso, mas seguindo requisitos rigorosamente)
                if item.get("status") == "used_as_asset" or item.get("linked_to_item_id") or item.get("asset_role"):
                    continue
                    
                title = item.get("title", "Sem título").lower()
                if any(x in title for x in ["briefing", "recommendation", "instrução", "prompt", "teste", "técnico"]):
                    continue
                    
                # Filtro por data
                published_at_str = item.get("published_at")
                fallback_flag = False
                pub_dt = None
                
                if published_at_str:
                    try:
                        dt = datetime.datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                        pub_dt = dt if dt.tzinfo else dt.replace(tzinfo=tz)
                    except Exception:
                        fallback_flag = True
                else:
                    fallback_flag = True
                    
                if not fallback_flag and pub_dt:
                    if pub_dt < cutoff_date:
                        continue  # Fora da janela
                
                # Se cair no fallback, incluímos opcionalmente mas marcamos (como sugerido)
                item["_is_fallback"] = fallback_flag
                
                qualified_posts.append(item)
                
        # Preparar dados para o prompt
        source_learning_count = 0
        posts_context = []
        
        for p in qualified_posts:
            p_data = {
                "titulo": p.get("title", "Sem título"),
                "tipo": p.get("format", "Não especificado"),
                "published_at": p.get("published_at", "Ausente"),
                "url": p.get("published_url", "Ausente"),
                "tracking_status": p.get("post_publish_tracking_status", "Nenhum"),
                "has_metrics": False,
                "has_learning": False,
                "metrics_data": p.get("metrics", {}).get("latest", {})
            }
            if p_data["metrics_data"]:
                p_data["has_metrics"] = True
                
            learning_file = p.get("editorial_learning_file")
            if learning_file:
                abs_learning = os.path.join(self.base_dir, learning_file.replace("/", os.sep))
                if os.path.exists(abs_learning):
                    with open(abs_learning, "r", encoding="utf-8") as f:
                        p_data["learning_content"] = f.read()
                        p_data["has_learning"] = True
                        source_learning_count += 1
                        
            analysis_file = p.get("post_publish_analysis_file")
            if analysis_file:
                abs_analysis = os.path.join(self.base_dir, analysis_file.replace("/", os.sep))
                if os.path.exists(abs_analysis):
                    with open(abs_analysis, "r", encoding="utf-8") as f:
                        p_data["analysis_content"] = f.read()
                        
            posts_context.append(p_data)
            
        metrics_limitada = ""
        # Verifica se pelo menos 30% dos posts possuem metricas, senao injeta a limitacao
        if len(qualified_posts) == 0:
            return {"status": "error", "message": "Nenhum post publicado principal encontrado na janela fornecida."}
            
        metrics_ratio = sum(1 for p in posts_context if p["has_metrics"]) / len(posts_context)
        if metrics_ratio < 0.5:
            metrics_limitada = "\nA memória estratégica está limitada porque ainda há poucas métricas importadas."
            
        prompt = f"""Você é o Strategic Memory Agent do BrandOS.

Sua tarefa é transformar aprendizados editoriais, métricas manuais, análises qualitativas e histórico de posts publicados em uma memória estratégica para orientar o CMO Agent.

Não invente métricas.
Não invente resultado.
Não afirmar que algo funcionou sem evidência.
Separe:
- dado observado
- leitura editorial
- hipótese estratégica
- recomendação prática

{metrics_limitada}

### DADOS DOS POSTS ({len(qualified_posts)} analisados nos últimos {window_days} dias):
"""
        for idx, p in enumerate(posts_context):
            prompt += f"\n\n--- POST {idx+1} ---\n"
            prompt += f"Título: {p['titulo']}\n"
            prompt += f"Data: {p['published_at']}\n"
            prompt += f"URL: {p['url']}\n"
            if p.get("metrics_data"):
                prompt += f"Métricas: {json.dumps(p['metrics_data'], ensure_ascii=False)}\n"
            if p.get("learning_content"):
                prompt += f"\nAPRENDIZADO EDITORIAL:\n{p['learning_content']}\n"
            if p.get("analysis_content"):
                prompt += f"\nANÁLISE QUALITATIVA:\n{p['analysis_content']}\n"

        if notes:
            prompt += f"\n\n### NOTAS DIRECIONAIS:\n{notes}\n"

        prompt += """

Gerar relatório em Markdown EXATAMENTE com estas seções:

# Memória Estratégica do CMO Agent

## 1. Resumo executivo

## 2. Posts considerados

## 3. Padrões percebidos

## 4. Sinais positivos

## 5. Sinais de atenção

## 6. Temas que merecem continuidade

## 7. Temas ou abordagens a evitar

## 8. Recomendações para a próxima semana

## 9. Briefing estratégico para o CMO Agent

## 10. Limitações da memória

Tom:
- português do Brasil
- direto
- estratégico
- sem floreio
- sem prometer resultado
- sem inventar dados
"""

        system_prompt = "Você é o Strategic Memory Agent do BrandOS."
        try:
            markdown_content = self.llm.generate_content(system_prompt, prompt)
        except Exception as e:
            return {"status": "error", "message": f"Erro ao gerar memória estratégica no LLM: {str(e)}"}
            
        # Preparar pastas e salvar markdown localmente
        mem_dir = os.path.join(self.base_dir, "data", "generated", "strategic-memory")
        os.makedirs(mem_dir, exist_ok=True)
        
        now = datetime.datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")
        date_str = datetime.datetime.now(tz).strftime("%Y-%m-%d")
        timestamp_str = datetime.datetime.now(tz).strftime("%Y%m%d-%H%M%S")
        memory_id = f"strategic-memory-{timestamp_str}"
        
        filename = f"{date_str}-{memory_id}.md"
        filepath = os.path.join(mem_dir, filename)
        rel_filepath = os.path.join("data", "generated", "strategic-memory", filename).replace("\\", "/")
        
        # 12. Escrita Segura MD
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        # Atualizar index.json atomicamente
        index_path = os.path.join(mem_dir, "index.json")
        index_data = {"memories": []}
        
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    index_data = json.load(f)
                    if not isinstance(index_data, dict) or "memories" not in index_data:
                        raise ValueError("Estrutura inválida.")
            except Exception as e:
                # E: index corrompido -> fazer backup e resetar
                backup_path = index_path + f".backup-{timestamp_str}"
                shutil.copy2(index_path, backup_path)
                index_data = {"memories": []}
                
        new_entry = {
            "id": memory_id,
            "file": rel_filepath,
            "generated_at": now,
            "window_days": window_days,
            "source_posts_count": len(qualified_posts),
            "source_learning_count": source_learning_count,
            "notes_provided": bool(notes)
        }
        
        index_data["memories"].append(new_entry)
        
        fd, temp_path = tempfile.mkstemp(dir=mem_dir)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, index_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return {"status": "error", "message": f"Erro ao atualizar index.json: {str(e)}"}
            
        return {
            "status": "success",
            "memory_file": rel_filepath,
            "memory_id": memory_id,
            "generated_at": now,
            "source_posts_count": len(qualified_posts),
            "source_learning_count": source_learning_count
        }


    def generate_cmo_recommendation_with_memory(self, confirm: bool = True, window_days: int = 30, notes: str = None) -> dict:
        import os, json, tempfile, shutil
        import datetime
        import zoneinfo
        
        if not confirm:
            return {"status": "error", "message": "Confirmação necessária."}
            
        if not isinstance(window_days, int) or window_days < 7 or window_days > 180:
            return {"status": "error", "message": "O parâmetro window_days deve ser um número inteiro entre 7 e 180."}
            
        # 1. Carregar Memória Estratégica (Read-only)
        latest_memory = self.get_latest_strategic_memory()
        memory_content = "Não há memória estratégica suficiente. A recomendação abaixo é preliminar."
        memory_id = None
        if latest_memory and latest_memory.get("content"):
            memory_content = latest_memory["content"]
            memory_id = latest_memory.get("id")
            
        # 2. Ler publication-log de forma segura, SOMENTE LEITURA
        history = self.history_repo.load()
        if not history:
            return {"status": "error", "message": "Registry vazio."}
            
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_aware = datetime.datetime.now(tz)
        cutoff_date = now_aware - datetime.timedelta(days=window_days)
        
        qualified_posts = []
        
        for entry in history:
            for item in entry.get("items", []):
                if item.get("status") != "published":
                    continue
                    
                is_main, _ = self._is_main_publication(item)
                if not is_main:
                    continue
                    
                if item.get("status") == "used_as_asset" or item.get("linked_to_item_id") or item.get("asset_role"):
                    continue
                    
                title = item.get("title", "Sem título").lower()
                if any(x in title for x in ["briefing", "recommendation", "instrução", "prompt", "teste", "técnico"]):
                    continue
                    
                published_at_str = item.get("published_at")
                fallback_flag = False
                pub_dt = None
                
                if published_at_str:
                    try:
                        dt = datetime.datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                        pub_dt = dt if dt.tzinfo else dt.replace(tzinfo=tz)
                    except Exception:
                        fallback_flag = True
                else:
                    fallback_flag = True
                    
                if not fallback_flag and pub_dt:
                    if pub_dt < cutoff_date:
                        continue  # Fora da janela
                
                qualified_posts.append(item)
                
        # 3. Preparar dados para o prompt
        source_learning_count = 0
        posts_context = []
        
        for p in qualified_posts:
            p_data = {
                "titulo": p.get("title", "Sem título"),
                "tipo": p.get("format", "Não especificado"),
                "published_at": p.get("published_at", "Ausente"),
                "url": p.get("published_url", "Ausente"),
                "tracking_status": p.get("post_publish_tracking_status", "Nenhum"),
                "has_metrics": False
            }
            metrics_data = p.get("metrics", {}).get("latest", {})
            if metrics_data:
                p_data["metrics_data"] = metrics_data
                p_data["has_metrics"] = True
                
            learning_file = p.get("editorial_learning_file")
            if learning_file:
                abs_learning = os.path.join(self.base_dir, learning_file.replace("/", os.sep))
                if os.path.exists(abs_learning):
                    with open(abs_learning, "r", encoding="utf-8") as f:
                        p_data["learning_content"] = f.read()
                        source_learning_count += 1
                        
            analysis_file = p.get("post_publish_analysis_file")
            if analysis_file:
                abs_analysis = os.path.join(self.base_dir, analysis_file.replace("/", os.sep))
                if os.path.exists(abs_analysis):
                    with open(abs_analysis, "r", encoding="utf-8") as f:
                        p_data["analysis_content"] = f.read()
                        
            posts_context.append(p_data)
            
        metrics_limitada = ""
        if len(posts_context) > 0:
            metrics_ratio = sum(1 for p in posts_context if p["has_metrics"]) / len(posts_context)
            if metrics_ratio < 0.5:
                metrics_limitada = "\nA recomendação está limitada porque ainda há poucas métricas importadas."
        else:
            metrics_limitada = "\nA recomendação está limitada porque ainda há poucas métricas importadas."

        # 4. Construção do Prompt do CMO Agent
        system_prompt = "Você é o CMO Agent do BrandOS."
        
        prompt = f"""Sua tarefa é gerar uma recomendação estratégica para a próxima semana editorial, usando a memória estratégica mais recente e os dados locais disponíveis.

Você não deve gerar posts finais.
Você não deve criar calendário automaticamente.
Você não deve publicar nada.
Você não deve inventar métricas.
Você não deve afirmar que algo funcionou sem evidência.

Você deve separar claramente:
- dado observado
- hipótese editorial
- recomendação prática
- limitação da análise

### MEMÓRIA ESTRATÉGICA ATUAL:
{memory_content}

{metrics_limitada}

### DADOS RECENTES DOS ÚLTIMOS {window_days} DIAS ({len(posts_context)} posts analisados):
"""
        for idx, p in enumerate(posts_context):
            prompt += f"\n--- POST RECENTE {idx+1} ---\n"
            prompt += f"Título: {p['titulo']}\n"
            if p.get("metrics_data"):
                prompt += f"Métricas: {json.dumps(p['metrics_data'], ensure_ascii=False)}\n"
            if p.get("learning_content"):
                prompt += f"\nAPRENDIZADO:\n{p.get('learning_content')}\n"
            if p.get("analysis_content"):
                prompt += f"\nANÁLISE:\n{p.get('analysis_content')}\n"

        if notes:
            prompt += f"\n\n### NOTAS DO USUÁRIO:\n{notes}\n"

        prompt += """
Gerar relatório em Markdown EXATAMENTE com estas seções:

# Recomendação Estratégica da Próxima Semana

## 1. Diagnóstico rápido
## 2. O que aprendemos até agora
## 3. O que continuar
## 4. O que evitar
## 5. Temas recomendados para a próxima semana
## 6. Formatos recomendados
## 7. Sugestão de agenda semanal
## 8. Briefing recomendado para aprovação humana
## 9. Riscos e cuidados
## 10. Próxima ação sugerida

Tom:
- português do Brasil
- direto
- estratégico
- prático
- sem floreio
- sem prometer resultado
- sem inventar dados
"""

        try:
            markdown_content = self.llm.generate_content(system_prompt, prompt)
        except Exception as e:
            return {"status": "error", "message": f"Erro ao gerar recomendação do CMO Agent no LLM: {str(e)}"}
            
        # 5. Salvar recomendação
        cmo_dir = os.path.join(self.base_dir, "data", "generated", "cmo-recommendations")
        os.makedirs(cmo_dir, exist_ok=True)
        
        now = datetime.datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")
        date_str = datetime.datetime.now(tz).strftime("%Y-%m-%d")
        timestamp_str = datetime.datetime.now(tz).strftime("%Y%m%d-%H%M%S")
        recommendation_id = f"cmo-recommendation-memory-{timestamp_str}"
        
        filename = f"{date_str}-{recommendation_id}.md"
        filepath = os.path.join(cmo_dir, filename)
        rel_filepath = os.path.join("data", "generated", "cmo-recommendations", filename).replace("\\", "/")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        # 6. Atualizar index.json das recomendações
        index_path = os.path.join(cmo_dir, "index.json")
        index_data = {"recommendations": []}
        
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    index_data = json.load(f)
                    if not isinstance(index_data, dict) or "recommendations" not in index_data:
                        raise ValueError("Estrutura inválida.")
            except Exception as e:
                # Backup em caso de corrompimento
                backup_path = index_path + f".backup-{timestamp_str}"
                shutil.copy2(index_path, backup_path)
                index_data = {"recommendations": []}
                
        new_entry = {
            "id": recommendation_id,
            "file": rel_filepath,
            "generated_at": now,
            "window_days": window_days,
            "used_strategic_memory": bool(memory_id),
            "strategic_memory_id": memory_id,
            "source_posts_count": len(qualified_posts),
            "source_learning_count": source_learning_count,
            "notes_provided": bool(notes),
            "status": "draft_recommendation"
        }
        
        index_data["recommendations"].append(new_entry)
        
        fd, temp_path = tempfile.mkstemp(dir=cmo_dir)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, index_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return {"status": "error", "message": f"Erro ao atualizar index.json: {str(e)}"}
            
        return {
            "status": "success",
            "recommendation_file": rel_filepath,
            "recommendation_id": recommendation_id,
            "generated_at": now,
            "used_strategic_memory": bool(memory_id),
            "strategic_memory_id": memory_id
        }



    def edit_briefing(self, filename: str, new_content: str, confirm: bool = True) -> dict:
        import os, tempfile, shutil
        if not confirm:
            return {"status": "error", "message": "Confirmação necessária para edição."}
            
        briefings_dir = os.path.join(self.base_dir, "data", "generated", "briefings")
        file_path = os.path.join(briefings_dir, filename)
        if not os.path.exists(file_path):
            return {"status": "error", "message": "Briefing não encontrado."}
            
        # Backup
        backup_path = file_path + ".bak"
        shutil.copy2(file_path, backup_path)
        
        try:
            fd, temp_path = tempfile.mkstemp(dir=briefings_dir, text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as tf:
                tf.write(new_content)
            os.replace(temp_path, file_path)
        except Exception as e:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
            return {"status": "error", "message": f"Erro na edição: {e}"}
            
        return {"status": "success", "message": "Briefing atualizado com sucesso."}

    def approve_briefing(self, filename: str, confirm: bool = True, user: str = "BrandOS User") -> dict:
        import os, tempfile, shutil, datetime, zoneinfo, re
        if not confirm:
            return {"status": "error", "message": "Confirmação necessária."}
            
        briefings_dir = os.path.join(self.base_dir, "data", "generated", "briefings")
        file_path = os.path.join(briefings_dir, filename)
        if not os.path.exists(file_path):
            return {"status": "error", "message": "Briefing não encontrado."}
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        status_match = re.search(r'^Status:\s*(.*)$', content, re.MULTILINE | re.IGNORECASE)
        if not status_match:
            return {"status": "error", "message": "Status não encontrado no arquivo."}
            
        current_status = status_match.group(1).strip().lower()
        if current_status not in ['draft', 'reviewed']:
            return {"status": "error", "message": f"Não é possível aprovar um briefing com status '{current_status}'."}
            
        # Modifica status
        content = re.sub(r'^(Status:\s*).*$', r'Status: approved', content, flags=re.MULTILINE | re.IGNORECASE)
        
        # Adiciona Data de aprovação
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_str = datetime.datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")
        
        lines = content.split('\\n')
        # Procura onde inserir (depois do header existente)
        insert_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("## ") or line.startswith("# 1."):
                insert_idx = i
                break
        
        if insert_idx == -1:
            insert_idx = len(lines)
            
        while insert_idx > 0 and lines[insert_idx-1].strip() == '':
            insert_idx -= 1
            
        approval_meta = [f"Data de aprovação: {now_str}", f"Aprovado por: {user}"]
        lines = lines[:insert_idx] + approval_meta + [""] + lines[insert_idx:]
        
        new_content = "\\n".join(lines)
        
        # Backup and Save
        backup_path = file_path + ".bak"
        shutil.copy2(file_path, backup_path)
        
        try:
            fd, temp_path = tempfile.mkstemp(dir=briefings_dir, text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as tf:
                tf.write(new_content)
            os.replace(temp_path, file_path)
        except Exception as e:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
            return {"status": "error", "message": f"Erro ao aprovar: {e}"}
            
        return {"status": "success", "message": "Briefing aprovado com sucesso."}

    def create_briefing_from_cmo_recommendation(self, recommendation_id: str, confirm: bool = True, notes: str = None) -> dict:
        import os, json
        import datetime
        import zoneinfo
        import re
        
        if not confirm:
            return {"status": "error", "message": "Confirmação necessária."}
            
        cmo_index_path = os.path.join(self.base_dir, "data", "generated", "cmo-recommendations", "index.json")
        if not os.path.exists(cmo_index_path):
            return {"status": "error", "message": "Índice de recomendações do CMO não encontrado."}
            
        target_rec = None
        try:
            with open(cmo_index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for rec in data.get("recommendations", []):
                    if rec.get("id") == recommendation_id:
                        target_rec = rec
                        break
        except Exception as e:
            return {"status": "error", "message": f"Erro ao ler índice: {e}"}
            
        if not target_rec:
            return {"status": "error", "message": "Recomendação não encontrada."}
            
        file_rel = target_rec.get("file")
        if not file_rel:
            return {"status": "error", "message": "Arquivo de recomendação inválido."}
            
        rec_path = os.path.join(self.base_dir, file_rel.replace("/", os.sep))
        if not os.path.exists(rec_path):
            return {"status": "error", "message": "Arquivo físico da recomendação não encontrado."}
            
        with open(rec_path, "r", encoding="utf-8") as f:
            md_content = f.read()
            
        def extract_section(text, section_title):
            pattern = re.compile(rf"##\s+\d+\.\s*{re.escape(section_title)}.*?\n(.*?)(?=\n##\s+\d+\.|$)", re.DOTALL | re.IGNORECASE)
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
            return "Seção não encontrada na recomendação original."
            
        contexto_estrat = extract_section(md_content, "Diagnóstico rápido") + "\n\n" + extract_section(md_content, "O que aprendemos até agora")
        objetivo = extract_section(md_content, "Briefing recomendado para aprovação humana")
        temas = extract_section(md_content, "Temas recomendados para a próxima semana")
        formatos = extract_section(md_content, "Formatos recomendados")
        agenda = extract_section(md_content, "Sugestão de agenda semanal")
        continuar = extract_section(md_content, "O que continuar")
        evitar = extract_section(md_content, "O que evitar")
        riscos = extract_section(md_content, "Riscos e cuidados")
        
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now = datetime.datetime.now(tz)
        timestamp_str = now.strftime("%Y%m%d-%H%M%S")
        date_str = now.strftime("%Y-%m-%d")
        created_at = now.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        safe_rec_id = re.sub(r'[^a-zA-Z0-9_-]', '', recommendation_id)
        
        briefing_filename = f"{date_str}-briefing-from-cmo-{safe_rec_id}-{timestamp_str}.md"
        briefings_dir = os.path.join(self.base_dir, "data", "generated", "briefings")
        os.makedirs(briefings_dir, exist_ok=True)
        
        briefing_path = os.path.join(briefings_dir, briefing_filename)
        
        obs_humanas = notes if notes else "Nenhuma observação humana adicional informada."
        
        briefing_md = f"""# Briefing Base — CMO Agent

Status: draft
Fonte: CMO Recommendation
Recommendation ID: {recommendation_id}
Data de criação: {created_at}
Origem técnica: cmo_recommendation

## 1. Contexto estratégico

{contexto_estrat}

## 2. Objetivo da semana

{objetivo}

## 3. Temas sugeridos

{temas}

## 4. Formatos sugeridos

{formatos}

## 5. Agenda sugerida

{agenda}

## 6. Diretrizes editoriais

### O que continuar
{continuar}

### O que evitar
{evitar}

### Riscos e cuidados
{riscos}

## 7. Observações humanas

{obs_humanas}

## 8. Fonte original

Recommendation ID: {recommendation_id}
Arquivo original: {file_rel}

## 9. Próxima ação

Revisar, editar e aprovar este briefing antes de gerar qualquer semana editorial.
"""

        if os.path.exists(briefing_path):
            return {"status": "error", "message": "Arquivo já existe, evitando sobrescrita."}
            
        with open(briefing_path, "w", encoding="utf-8") as f:
            f.write(briefing_md)
            
        return {
            "status": "success",
            "briefing_file": f"data/generated/briefings/{briefing_filename}",
            "briefing_filename": briefing_filename,
            "recommendation_id": recommendation_id,
            "created_at": created_at
        }

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
        import os, json, tempfile, shutil
        from datetime import datetime
        import zoneinfo
        
        if not confirm:
            raise ValueError("Confirmação necessária.")
            
        log_path = os.path.join(self.base_dir, "data", "registry", "publication-log.json")
        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)
            
        target_idx = None
        for idx, i in enumerate(log_data):
            if i.get("item_id") == item_id:
                if self._is_asset(i):
                    raise ValueError("Assets vinculados não podem ser publicados como publicações principais.")
                if i.get("status") != "scheduled":
                    raise ValueError(f"Post possui status '{i.get('status')}'. É necessário estar 'scheduled' para marcar como ready.")
                target_idx = idx
                break
                
        if target_idx is None:
            raise ValueError("Post não encontrado.")
            
        # Backup
        backup_dir = os.path.join(self.base_dir, "data", "registry", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = os.path.join(backup_dir, f"publication-log-{timestamp}.json")
        shutil.copy2(log_path, backup_path)
        
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_str = datetime.now(tz).isoformat()
        
        log_data[target_idx]["status"] = "publishing_ready"
        log_data[target_idx]["publishing_ready_at"] = now_str
        log_data[target_idx]["updated_at"] = now_str
        
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(log_path), text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)
        os.replace(temp_path, log_path)
        
        return {"status": "success", "message": "Post marcado como pronto para publicação."}

    def mark_post_published(self, item_id: str, confirm: bool, published_url: str = None, published_at: str = None) -> dict:
        import os, json, tempfile, shutil
        from datetime import datetime
        import zoneinfo
        
        if not confirm:
            raise ValueError("Confirmação necessária.")
            
        log_path = os.path.join(self.base_dir, "data", "registry", "publication-log.json")
        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)
            
        target_idx = None
        for idx, i in enumerate(log_data):
            if i.get("item_id") == item_id:
                if self._is_asset(i):
                    raise ValueError("Assets vinculados não podem ser publicados como publicações principais.")
                if i.get("status") not in ["scheduled", "publishing_ready"]:
                    raise ValueError(f"Status '{i.get('status')}' não permitido para marcar como publicado.")
                target_idx = idx
                break
                
        if target_idx is None:
            raise ValueError("Post não encontrado.")
            
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        if published_at:
            try:
                datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except Exception:
                raise ValueError("Formato de published_at inválido.")
            pub_date = published_at
        else:
            pub_date = datetime.now(tz).isoformat()
            
        # Backup
        backup_dir = os.path.join(self.base_dir, "data", "registry", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = os.path.join(backup_dir, f"publication-log-{timestamp}.json")
        shutil.copy2(log_path, backup_path)
        
        log_data[target_idx]["status"] = "published"
        log_data[target_idx]["published_at"] = pub_date
        if published_url:
            log_data[target_idx]["published_url"] = published_url
        log_data[target_idx]["published_by"] = "human"
        log_data[target_idx]["publication_source"] = "manual_linkedin"
        log_data[target_idx]["updated_at"] = datetime.now(tz).isoformat()
        
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(log_path), text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)
        os.replace(temp_path, log_path)
        
        return {"status": "success", "message": "Post marcado como publicado."}

    def undo_post_published(self, item_id: str, confirm: bool, reason: str = None) -> dict:
        import os, json, tempfile, shutil
        from datetime import datetime
        import zoneinfo
        
        if not confirm:
            raise ValueError("Confirmação necessária.")
            
        log_path = os.path.join(self.base_dir, "data", "registry", "publication-log.json")
        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)
            
        target_idx = None
        for idx, i in enumerate(log_data):
            if i.get("item_id") == item_id:
                if self._is_asset(i):
                    raise ValueError("Assets vinculados não podem ser publicados como publicações principais.")
                if i.get("status") != "published":
                    raise ValueError(f"Post possui status '{i.get('status')}'. É necessário estar 'published' para desfazer.")
                target_idx = idx
                break
                
        if target_idx is None:
            raise ValueError("Post não encontrado.")
            
        # Backup
        backup_dir = os.path.join(self.base_dir, "data", "registry", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = os.path.join(backup_dir, f"publication-log-{timestamp}.json")
        shutil.copy2(log_path, backup_path)
        
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_str = datetime.now(tz).isoformat()
        
        item = log_data[target_idx]
        item["status"] = "scheduled"
        item["unpublished_at"] = now_str
        item["unpublished_by"] = "human"
        if reason:
            item["unpublished_reason"] = reason
        item["updated_at"] = now_str
        
        history_event = {
            "event": "undo_published",
            "from_status": "published",
            "to_status": "scheduled",
            "published_at": item.get("published_at"),
            "published_url": item.get("published_url"),
            "unpublished_at": now_str,
            "unpublished_by": "human",
            "reason": reason
        }
        
        if "publication_history" not in item:
            item["publication_history"] = []
        item["publication_history"].append(history_event)
        
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(log_path), text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)
        os.replace(temp_path, log_path)
        
        return {"status": "success", "message": "Marcação de publicação desfeita."}


    def normalize_registry_item_ids(self) -> dict:
        """Normaliza itens sem item_id gerando um novo ou usando id existente."""
        history = self.history_repo.load()
        if not history:
            return {"normalized_count": 0, "normalized_items": [], "warnings": ["Histórico vazio."]}
            
        import uuid
        from datetime import datetime
        
        normalized_count = 0
        normalized_items = []
        warnings = []
        
        for entry in history:
            items_to_process = entry.get("items", []) if "items" in entry else [entry]
            for item in items_to_process:
                if not item.get("item_id"):
                    if item.get("id"):
                        # Use existing id
                        item["item_id"] = item["id"]
                    else:
                        # Generate new
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
        """Retorna suspeitos para descarte em massa."""
        history = self.history_repo.load()
        suspects = []
        
        if not history:
            return {"suspects": suspects}
            
        for entry in history:
            items_to_process = entry.get("items", []) if "items" in entry else [entry]
            for item in items_to_process:
                identifier = self._get_item_identifier(item)
                title = item.get("title")
                
                reason = []
                if not identifier:
                    reason.append("Sem identifier")
                if not title or str(title).strip() == "":
                    reason.append("Título vazio")
                elif "Test" in str(title):
                    reason.append("Contém 'Test' no título")
                    
                sched = item.get("scheduled_at")
                if sched:
                    try:
                        from datetime import datetime
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
        """Descartar lista explícita de itens."""
        if not confirm:
            raise ValueError("Confirmação obrigatória.")
            
        history = self.history_repo.load()
        if not history:
            raise ValueError("Histórico vazio.")
            
        discarded_count = 0
        from datetime import datetime
        now_str = datetime.now().isoformat()
        
        for entry in history:
            items_to_process = entry.get("items", []) if "items" in entry else [entry]
            for item in items_to_process:
                identifier = self._get_item_identifier(item)
                if identifier in item_ids:
                    # Block published/assets
                    status = item.get("status")
                    if status == "published":
                        continue
                    if status == "used_as_asset" or item.get("linked_to_item_id") or item.get("asset_role"):
                        continue
                        
                    item["status"] = "discarded"
                    
                    if "discard_history" not in item:
                        item["discard_history"] = []
                        
                    item["discard_history"].append({
                        "discarded_at": now_str,
                        "reason": reason,
                        "previous_status": status
                    })
                    
                    # Clear operational fields
                    for field in ["scheduled_at", "scheduled_date", "scheduled_time", "scheduled_for"]:
                        item.pop(field, None)
                        
                    discarded_count += 1
                    
        if discarded_count > 0:
            self.history_repo.save(history)
            
        return {"discarded_count": discarded_count}


    def start_post_publish_tracking(self, item_id: str, confirm: bool = True) -> dict:
        if not confirm:
            return {"status": "error", "message": "Confirmação necessária."}
            
        history = self.list_history()
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
        
        self.save_history(history)
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
            
        history = self.list_history()
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
            
        self.save_history(history)
        return {"status": "success", "message": "Status de acompanhamento atualizado."}
