import json
import os
import shutil
import tempfile
import datetime
import zoneinfo


class CmoService:
    def __init__(self, base_dir: str, history_repo=None, llm_client=None, learning_service=None):
        self.base_dir = base_dir
        self.history_repo = history_repo
        self.llm = llm_client
        self.learning_service = learning_service
        self.cmo_dir = os.path.join(base_dir, "data", "generated", "cmo-recommendations")
        self.index_path = os.path.join(self.cmo_dir, "index.json")

    def _safe_recommendation(self, rec: dict) -> dict:
        status = rec.get("status", "active")
        briefing_file = rec.get("briefing_file") or rec.get("briefing_filename")
        safe_rec = {
            "id": rec.get("id", "sem-id"),
            "generated_at": rec.get("generated_at", "Data desconhecida"),
            "window_days": rec.get("window_days", 30),
            "used_strategic_memory": rec.get("used_strategic_memory", False),
            "source_posts_count": rec.get("source_posts_count", 0),
            "source_learning_count": rec.get("source_learning_count", 0),
            "file": rec.get("file", ""),
            "status": status,
            "briefing_file": briefing_file,
            "briefing_filename": rec.get("briefing_filename"),
        }
        if status in {"briefing_created", "used_for_briefing"} or briefing_file:
            safe_rec["workflow_state"] = "briefing_created"
            safe_rec["workflow_label"] = "Virou briefing"
        elif status == "archived":
            safe_rec["workflow_state"] = "archived"
            safe_rec["workflow_label"] = "Arquivada"
        else:
            safe_rec["workflow_state"] = "pending"
            safe_rec["workflow_label"] = "Nova recomendação"
        return safe_rec

    def _load_index(self) -> tuple[dict, str | None]:
        if not os.path.exists(self.index_path):
            return {"recommendations": []}, None

        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {"recommendations": []}, None
                return json.loads(content), None
        except json.JSONDecodeError:
            return {"recommendations": []}, "O arquivo de índice (index.json) está inválido."
        except Exception as e:
            return {"recommendations": []}, f"Erro ao ler recomendações: {str(e)}"

    def _deduplicate_recommendations(self, recommendations: list[dict]) -> tuple[list[dict], int]:
        sorted_recs = sorted(recommendations, key=lambda x: x.get("generated_at", ""), reverse=True)
        unique = []
        seen = set()
        duplicates = 0
        for rec in sorted_recs:
            key = rec.get("id") or rec.get("file") or f"unknown-{len(unique)}"
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            unique.append(self._safe_recommendation(rec))
        return unique, duplicates

    def list_recommendations(self) -> tuple[list, list, str | None]:
        inbox = self.list_recommendation_inbox()
        return (
            inbox["active_recommendations"] + inbox["recommendation_history"],
            inbox["archived_recommendations"],
            inbox["error_msg"],
        )

    def list_recommendation_inbox(self) -> dict:
        data, error_msg = self._load_index()
        unique_recs, duplicate_count = self._deduplicate_recommendations(data.get("recommendations", []))

        archived = [rec for rec in unique_recs if rec["workflow_state"] == "archived"]
        visible = [rec for rec in unique_recs if rec["workflow_state"] != "archived"]
        pending = [rec for rec in visible if rec["workflow_state"] == "pending"]

        active_recommendation = pending[0] if pending else None
        active_recommendations = [active_recommendation] if active_recommendation else []
        history = []
        for rec in visible:
            if active_recommendation and rec["id"] == active_recommendation["id"]:
                continue
            history.append(rec)

        return {
            "active_recommendation": active_recommendation,
            "active_recommendations": active_recommendations,
            "recommendation_history": history,
            "archived_recommendations": archived,
            "duplicate_count": duplicate_count,
            "total_count": len(data.get("recommendations", [])),
            "visible_count": len(visible),
            "error_msg": error_msg,
        }

    def archive_stale_recommendations(self, confirm: bool = True) -> dict:
        if not confirm:
            return {"status": "error", "message": "Confirmação obrigatória."}

        data, error_msg = self._load_index()
        if error_msg:
            return {"status": "error", "message": error_msg}

        recommendations = data.get("recommendations", [])
        if not recommendations:
            return {"status": "success", "message": "Não há recomendações para arquivar.", "archived_count": 0}

        unique_recs, _ = self._deduplicate_recommendations(recommendations)
        latest_pending_id = next((rec["id"] for rec in unique_recs if rec["workflow_state"] == "pending"), None)
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_str = datetime.datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")
        archived_count = 0
        seen = set()

        for rec in recommendations:
            rec_id = rec.get("id")
            is_duplicate = rec_id in seen
            seen.add(rec_id)
            should_archive = (
                rec.get("status") != "archived"
                and (is_duplicate or rec_id != latest_pending_id)
                and not rec.get("briefing_file")
                and rec.get("status") not in {"briefing_created", "used_for_briefing"}
            )
            if should_archive:
                rec["status"] = "archived"
                rec["archived_at"] = now_str
                rec["archived_by"] = "BrandOS maintenance"
                archived_count += 1

        if archived_count:
            self._write_index(data)

        return {
            "status": "success",
            "message": f"{archived_count} recomendação(ões) antiga(s) arquivada(s).",
            "archived_count": archived_count,
        }

    def mark_recommendation_briefing_created(self, recommendation_id: str, briefing_file: str, briefing_filename: str) -> None:
        data, error_msg = self._load_index()
        if error_msg:
            return

        changed = False
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_str = datetime.datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")
        for rec in data.get("recommendations", []):
            if rec.get("id") == recommendation_id:
                rec["status"] = "briefing_created"
                rec["briefing_file"] = briefing_file
                rec["briefing_filename"] = briefing_filename
                rec["briefing_created_at"] = now_str
                changed = True
        if changed:
            self._write_index(data)

    def _write_index(self, index_data: dict) -> None:
        os.makedirs(self.cmo_dir, exist_ok=True)
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        fd, temp_path = tempfile.mkstemp(dir=self.cmo_dir, prefix="index_", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=4)

        if os.path.exists(self.index_path):
            backup_path = self.index_path + f".backup-{datetime.datetime.now(tz).strftime('%Y%m%d%H%M%S')}"
            shutil.copy2(self.index_path, backup_path)
        os.replace(temp_path, self.index_path)

    def get_recommendation(self, recommendation_id: str) -> dict | None:
        if not os.path.exists(self.index_path):
            return None

        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None

        for rec in data.get("recommendations", []):
            if rec.get("id") == recommendation_id:
                return rec
        return None

    def read_recommendation_markdown(self, recommendation_id: str) -> tuple[dict | None, str | None]:
        recommendation = self.get_recommendation(recommendation_id)
        if not recommendation:
            return None, None

        file_rel = recommendation.get("file")
        if not file_rel:
            return recommendation, None

        file_path = os.path.join(self.base_dir, file_rel.replace("/", os.sep))
        if not os.path.exists(file_path):
            return recommendation, None

        with open(file_path, "r", encoding="utf-8") as f:
            return recommendation, f.read()

    def archive_cmo_recommendation(self, recommendation_id: str, confirm: bool = True) -> dict:
        if not confirm:
            return {"status": "error", "message": "Confirmação obrigatória."}

        if not os.path.exists(self.index_path):
            return {"status": "error", "message": "Índice de recomendações não encontrado."}

        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)

            recs = index_data.get("recommendations", [])
            target_idx = None
            for idx, rec in enumerate(recs):
                if rec.get("id") == recommendation_id:
                    target_idx = idx
                    break

            if target_idx is None:
                return {"status": "error", "message": "Recomendação não encontrada."}

            if recs[target_idx].get("status") == "archived":
                return {"status": "success", "message": "Recomendação já estava arquivada."}

            tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
            now_str = datetime.datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")

            recs[target_idx]["status"] = "archived"
            recs[target_idx]["archived_at"] = now_str
            recs[target_idx]["archived_by"] = "BrandOS User"

            self._write_index(index_data)

            return {"status": "success", "message": "Recomendação arquivada com sucesso."}
        except Exception as e:
            return {"status": "error", "message": f"Erro ao arquivar recomendação: {str(e)}"}
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

    def _validate_cmo_recommendation_specificity(self, text: str) -> bool:
        forbidden = [
            "[", "]", "Problema do Público", "Assunto Específico", 
            "Tópico Relevante", "conteúdo relevante", "tema interessante",
            "guia rápido de", "3 dicas essenciais para", "3 dicas para"
        ]
        text_lower = text.lower()
        for f in forbidden:
            if f.lower() in text_lower:
                return False
        return True

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

    def generate_cmo_recommendation_with_memory(self, confirm: bool = True, window_days: int = 30, notes: str = None) -> dict:
        import os, json, tempfile, shutil
        import datetime
        import zoneinfo
        import time
        
        if not confirm:
            return {"status": "error", "message": "Confirmação necessária."}
            
        # Proteção de idempotência
        cmo_dir = os.path.join(self.base_dir, "data", "generated", "cmo-recommendations")
        index_path = os.path.join(cmo_dir, "index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    index_data = json.load(f)
                    recs = index_data.get("recommendations", [])
                    if recs:
                        latest = sorted(recs, key=lambda x: x.get("generated_at", ""), reverse=True)[0]
                        latest_date_str = latest.get("generated_at")
                        if latest_date_str:
                            tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
                            dt = datetime.datetime.fromisoformat(latest_date_str.replace("Z", "+00:00"))
                            now_dt = datetime.datetime.now(tz)
                            if (now_dt - dt).total_seconds() < 120:
                                return {
                                    "status": "success",
                                    "idempotent": True,
                                    "recommendation_file": latest.get("file"),
                                    "recommendation_id": latest.get("id"),
                                    "generated_at": latest.get("generated_at"),
                                    "used_strategic_memory": latest.get("used_strategic_memory"),
                                    "strategic_memory_id": latest.get("strategic_memory_id")
                                }
            except Exception:
                pass
            
        if not isinstance(window_days, int) or window_days < 7 or window_days > 180:
            return {"status": "error", "message": "O parâmetro window_days deve ser um número inteiro entre 7 e 180."}
            
        # 1. Carregar Memória Estratégica (Read-only)
        latest_memory = self.learning_service.get_latest_strategic_memory() if self.learning_service else None
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
        system_prompt = """Você é o CMO Agent do BrandOS, responsável pela estratégia de marca pessoal de Leandro.
Você não é uma agência genérica. Você não deve gerar fórmulas vazias. Você não deve usar placeholders. Você não deve sugerir temas abstratos sem projeto concreto.

Você deve sempre trabalhar com projetos e territórios reais:
- Sentinela RJ: Civic Tech, dados públicos, contratos públicos, transparência, Python e IA aplicada.
- Hermes Lite: assistente pessoal real, agentes de IA, roteamento inteligente, modelo local vs cloud, produtividade com IA.
- BrandOS: sistema pessoal de marketing com IA, operação editorial, memória estratégica, aprendizado com métricas.
- Jornada do Leandro: transição para tecnologia, aprendizado público, construção de portfólio real, Python, IA aplicada.

Se houver excesso de Sentinela RJ no backlog, considerar Hermes Lite ou BrandOS para diversificar.
Se houver pouca métrica, dizer que a recomendação é limitada, mas ainda assim escolher um projeto concreto.

É proibido usar:
- colchetes com variáveis genéricas
- "[Problema do Público]"
- "[Assunto Específico]"
- "[Tópico Relevante]"
- "conteúdo relevante"
- "tema interessante"
- "guia rápido" sem tema real
- "3 dicas" sem problema real e específico

A recomendação deve ser prática e pronta para virar briefing humano.
"""
        
        prompt = f"""Sua tarefa é gerar uma recomendação estratégica para a próxima semana editorial, usando a memória estratégica mais recente e os dados locais disponíveis.

Você não deve gerar posts finais. Não crie calendário automaticamente. Não invente métricas. Não afirme que algo funcionou sem evidência.

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
Diagnóstico específico do momento atual: backlog, risco de repetição, projeto mais indicado, limitação de métricas (se houver).

## 2. Projeto recomendado
Escolher um projeto real (Sentinela RJ, Hermes Lite, BrandOS, Estudos de Python/IA aplicada) e explicar por quê.

## 3. Tema central da semana
Tema concreto, sem placeholder.

## 4. Justificativa estratégica
Explicar por que esse tema ajuda a marca pessoal do Leandro agora.

## 5. O que continuar
Pontos que devem continuar, baseados nos dados ou no posicionamento.

## 6. O que evitar
Coisas concretas: excesso de Sentinela RJ, posts genéricos de IA, conteúdo sem projeto real, CTA fraco, jargão técnico demais.

## 7. Grade sugerida da semana
Segunda: Tema específico. Objetivo do post. Formato sugerido.
Quarta: Tema específico. Objetivo do post. Formato sugerido.
Sexta: Tema específico. Objetivo do post. Formato sugerido.

## 8. Briefing recomendado para aprovação humana
Um briefing curto e concreto, pronto para o usuário revisar.

## 9. Riscos e cuidados
Riscos específicos da semana.

## 10. Próxima ação sugerida
Dizer exatamente o que o usuário deve fazer: salvar como briefing, revisar, aprovar, gerar semana, ou publicar backlog pendente.

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
            
            # Pós-validação anti-placeholder
            if not self._validate_cmo_recommendation_specificity(markdown_content):
                retry_prompt = prompt + "\n\nA resposta anterior usou placeholders ou linguagem genérica. Reescreva com projetos reais do Leandro e sem nenhum placeholder."
                print("[CMO Agent] Placeholder detectado. Tentando correção (retry)...")
                markdown_content = self.llm.generate_content(system_prompt, retry_prompt)
                
                if not self._validate_cmo_recommendation_specificity(markdown_content):
                    print("[CMO Agent] Fallback genérico ainda detectado. Adicionando aviso.")
                    markdown_content = "> [!WARNING]\n> **AVISO**: Esta recomendação pode estar genérica e deve ser revisada manualmente.\n\n" + markdown_content
                    
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
