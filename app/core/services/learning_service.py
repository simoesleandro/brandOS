from app.core.repositories.history_repository import HistoryRepository


class LearningService:
    def __init__(self, base_dir: str, history_repo: HistoryRepository, llm_client):
        self.base_dir = base_dir
        self.history_repo = history_repo
        self.llm = llm_client

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
            
        is_main, _ = self._is_main_publication(target_item)
        if not is_main:
            return {"status": "error", "message": "Não é possível gerar aprendizado para este tipo de item (asset/técnico)."}
            
        if target_item.get("status") != "published":
            return {"status": "error", "message": "Item precisa estar publicado para gerar aprendizado."}
            
        # Preparar pasta
        base_dir = self.base_dir
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
