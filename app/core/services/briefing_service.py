import os
import json
import re
import shutil
import tempfile
import time
import zoneinfo
from datetime import datetime, timedelta

from app.workflows.weekly_workflow import WeeklyGenerationRequest, run_weekly_workflow


class BriefingService:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.briefings_dir = os.path.join(base_dir, "data", "generated", "briefings")

    def list_briefings(self) -> list:
        if not os.path.exists(self.briefings_dir):
            return []

        briefings = []
        for filename in os.listdir(self.briefings_dir):
            if not filename.endswith(".md"):
                continue

            file_path = os.path.join(self.briefings_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                created_at = "Desconhecido"
                source = "Desconhecida"
                status = "Desconhecido"
                generated_folder = None

                for line in lines[:50]:
                    if line.startswith("Data de criação:"):
                        created_at = line.replace("Data de criação:", "").strip()
                    elif line.startswith("Fonte:"):
                        source = line.replace("Fonte:", "").strip()
                    elif line.startswith("Status:"):
                        status = line.replace("Status:", "").strip()
                    elif line.startswith("Generated folder:"):
                        generated_folder = line.replace("Generated folder:", "").strip()
                    elif line.startswith("Pasta gerada:") and not generated_folder:
                        generated_folder = line.replace("Pasta gerada:", "").strip()

                briefings.append({
                    "filename": filename,
                    "created_at": created_at,
                    "source": source,
                    "status": status,
                    "generated_folder": generated_folder,
                    "sort_key": filename
                })
            except Exception as e:
                print(f"Erro ao ler briefing {filename}: {e}")

        briefings.sort(key=lambda x: x["sort_key"], reverse=True)
        return briefings

    def read_briefing(self, filename: str) -> str:
        filename = os.path.basename(filename)
        file_path = os.path.join(self.briefings_dir, filename)

        if not os.path.exists(file_path):
            raise FileNotFoundError("Briefing não encontrado.")

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def prepare_week_from_briefing(self, filename: str) -> dict:
        content = self.read_briefing(filename)

        today = datetime.now()
        days_until_monday = 0 - today.weekday()
        if days_until_monday <= 0:
            days_until_monday += 7
        next_monday = (today + timedelta(days=days_until_monday)).strftime("%Y-%m-%d")

        metadata = self._extract_generation_metadata(content)
        return {
            "projeto": metadata["project"],
            "tema_central": metadata["theme"],
            "canal": "LinkedIn",
            "quantidade_posts": 3,
            "frequencia": metadata["frequency"],
            "data_inicial": next_monday,
            "warnings": metadata["warnings"],
        }

    def generate_week_from_briefing(self, filename: str, options: dict) -> dict:
        briefing_content = self.read_briefing(filename)
        self._validate_approved_for_generation(briefing_content)

        start_date = options.get("start_date") or options.get("data_inicial") or ""
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Data inicial inválida. Use o formato YYYY-MM-DD.")

        metadata = self._extract_generation_metadata(briefing_content)
        project = (
            options.get("projeto")
            or options.get("project")
            or options.get("project_slug")
            or metadata["project"]
        )
        theme = options.get("tema_central") or options.get("theme") or metadata["theme"]
        frequency = options.get("frequencia") or options.get("frequency") or metadata["frequency"]

        request = WeeklyGenerationRequest(
            briefing_content=briefing_content,
            project=project,
            theme=theme,
            start_date=start_date,
            frequency=frequency,
            source_briefing_file=os.path.basename(filename),
            source_recommendation_id=self._extract_recommendation_id(briefing_content),
        )

        result = run_weekly_workflow(base_dir=self.base_dir, request=request)
        self._mark_briefing_generated(filename, result["folder"])

        return {
            "status": "success",
            "folder": result["folder"],
            "files": result.get("files", []),
            "item_ids": result.get("item_ids", []),
            "warnings": metadata["warnings"] + result.get("warnings", []),
        }

    def save_cmo_recommendation_as_briefing(self, recommendation_text: str) -> str:
        if not recommendation_text or not recommendation_text.strip():
            raise ValueError("Nenhuma recomendação disponível para salvar como briefing.")

        now = datetime.now()
        os.makedirs(self.briefings_dir, exist_ok=True)

        filename = now.strftime("%Y-%m-%d-%H%M-next-week-briefing.md")
        file_path = os.path.join(self.briefings_dir, filename)

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

        return f"data/generated/briefings/{filename}"

    def edit_briefing(self, filename: str, new_content: str, confirm: bool = True) -> dict:
        if not confirm:
            return {"status": "error", "message": "Confirmação necessária para edição."}

        file_path = self._briefing_path(filename)
        if not os.path.exists(file_path):
            return {"status": "error", "message": "Briefing não encontrado."}

        backup_path = file_path + ".bak"
        shutil.copy2(file_path, backup_path)

        try:
            fd, temp_path = tempfile.mkstemp(dir=self.briefings_dir, text=True)
            with os.fdopen(fd, "w", encoding="utf-8") as tf:
                tf.write(new_content)
            os.replace(temp_path, file_path)
        except Exception as e:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
            return {"status": "error", "message": f"Erro na edição: {e}"}

        return {"status": "success", "message": "Briefing atualizado com sucesso."}

    def approve_briefing(self, filename: str, confirm: bool = True, user: str = "BrandOS User") -> dict:
        return self._transition_briefing_status(
            filename=filename,
            confirm=confirm,
            user=user,
            allowed_statuses=["draft", "reviewed"],
            new_status="approved",
            timestamp_label="Data de aprovação",
            user_label="Aprovado por",
            success_message="Briefing aprovado com sucesso.",
            error_action="aprovar",
        )

    def archive_briefing(self, filename: str, confirm: bool = True, user: str = "BrandOS User") -> dict:
        return self._transition_briefing_status(
            filename=filename,
            confirm=confirm,
            user=user,
            allowed_statuses=["draft", "reviewed"],
            new_status="archived",
            timestamp_label="Arquivado em",
            user_label="Arquivado por",
            success_message="Briefing arquivado com sucesso.",
            error_action="arquivar",
        )

    def create_briefing_from_cmo_recommendation(self, recommendation_id: str, confirm: bool = True, notes: str = None) -> dict:
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

        contexto_estrat = self._extract_section(md_content, "Diagnóstico rápido") + "\n\n" + self._extract_section(md_content, "O que aprendemos até agora")
        objetivo = self._extract_section(md_content, "Briefing recomendado para aprovação humana")
        temas = self._extract_section(md_content, "Temas recomendados para a próxima semana")
        formatos = self._extract_section(md_content, "Formatos recomendados")
        agenda = self._extract_section(md_content, "Sugestão de agenda semanal")
        continuar = self._extract_section(md_content, "O que continuar")
        evitar = self._extract_section(md_content, "O que evitar")
        riscos = self._extract_section(md_content, "Riscos e cuidados")

        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now = datetime.now(tz)
        timestamp_str = now.strftime("%Y%m%d-%H%M%S")
        date_str = now.strftime("%Y-%m-%d")
        created_at = now.strftime("%Y-%m-%dT%H:%M:%S%z")
        safe_rec_id = re.sub(r"[^a-zA-Z0-9_-]", "", recommendation_id)

        os.makedirs(self.briefings_dir, exist_ok=True)

        current_time = time.time()
        for b_file in os.listdir(self.briefings_dir):
            if not b_file.endswith(".md"):
                continue
            if safe_rec_id in b_file:
                b_path = os.path.join(self.briefings_dir, b_file)
                try:
                    if current_time - os.path.getmtime(b_path) < 120:
                        self._mark_cmo_recommendation_used(recommendation_id, f"data/generated/briefings/{b_file}", b_file)
                        return {
                            "status": "success",
                            "briefing_file": f"data/generated/briefings/{b_file}",
                            "briefing_filename": b_file,
                            "recommendation_id": recommendation_id,
                            "idempotent": True,
                            "message": "Briefing já criado recentemente para esta recomendação."
                        }
                except Exception:
                    pass

        briefing_filename = f"{date_str}-briefing-from-cmo-{safe_rec_id}-{timestamp_str}.md"
        briefing_path = os.path.join(self.briefings_dir, briefing_filename)
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

        briefing_file = f"data/generated/briefings/{briefing_filename}"
        self._mark_cmo_recommendation_used(recommendation_id, briefing_file, briefing_filename)

        return {
            "status": "success",
            "briefing_file": briefing_file,
            "briefing_filename": briefing_filename,
            "recommendation_id": recommendation_id,
            "created_at": created_at,
            "idempotent": False
        }

    def _mark_cmo_recommendation_used(self, recommendation_id: str, briefing_file: str, briefing_filename: str) -> None:
        try:
            from app.core.services.cmo_service import CmoService

            CmoService(self.base_dir).mark_recommendation_briefing_created(
                recommendation_id=recommendation_id,
                briefing_file=briefing_file,
                briefing_filename=briefing_filename,
            )
        except Exception:
            pass

    def _transition_briefing_status(
        self,
        filename: str,
        confirm: bool,
        user: str,
        allowed_statuses: list[str],
        new_status: str,
        timestamp_label: str,
        user_label: str,
        success_message: str,
        error_action: str,
    ) -> dict:
        if not confirm:
            return {"status": "error", "message": "Confirmação necessária."}

        file_path = self._briefing_path(filename)
        if not os.path.exists(file_path):
            return {"status": "error", "message": "Briefing não encontrado."}

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        status_match = re.search(r"^Status:\s*(.*)$", content, re.MULTILINE | re.IGNORECASE)
        if not status_match:
            return {"status": "error", "message": "Status não encontrado no arquivo."}

        current_status = status_match.group(1).strip().lower()
        if current_status not in allowed_statuses:
            return {"status": "error", "message": f"Não é possível {error_action} um briefing com status '{current_status}'."}

        content = re.sub(r"^(Status:\s*).*$", f"Status: {new_status}", content, flags=re.MULTILINE | re.IGNORECASE)

        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        now_str = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")

        lines = content.split("\n")
        insert_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("## ") or line.startswith("# 1."):
                insert_idx = i
                break

        if insert_idx == -1:
            insert_idx = len(lines)

        while insert_idx > 0 and lines[insert_idx - 1].strip() == "":
            insert_idx -= 1

        metadata = [f"{timestamp_label}: {now_str}", f"{user_label}: {user}"]
        new_content = "\n".join(lines[:insert_idx] + metadata + [""] + lines[insert_idx:])

        backup_path = file_path + ".bak"
        shutil.copy2(file_path, backup_path)

        try:
            fd, temp_path = tempfile.mkstemp(dir=self.briefings_dir, text=True)
            with os.fdopen(fd, "w", encoding="utf-8") as tf:
                tf.write(new_content)
            os.replace(temp_path, file_path)
        except Exception as e:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
            return {"status": "error", "message": f"Erro ao {error_action}: {e}"}

        return {"status": "success", "message": success_message}

    def _extract_section(self, text: str, section_title: str) -> str:
        pattern = re.compile(rf"##\s+\d+\.\s*{re.escape(section_title)}.*?\n(.*?)(?=\n##\s+\d+\.|$)", re.DOTALL | re.IGNORECASE)
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
        return "Seção não encontrada na recomendação original."

    def _validate_approved_for_generation(self, content: str) -> None:
        status_match = re.search(r"^\s*Status:\s*(.*)\s*$", content, re.IGNORECASE | re.MULTILINE)
        if not status_match:
            raise ValueError("Status não encontrado no briefing.")

        status = status_match.group(1).strip().lower()
        if status not in ["briefing_aprovado", "approved"]:
            raise ValueError(f"Não é possível gerar semana a partir de um briefing com status '{status}'. O status deve ser 'approved'.")

        if re.search(r"Generated folder:|Pasta gerada:", content, re.IGNORECASE):
            raise ValueError("Este briefing já gerou uma semana.")

    def _extract_generation_metadata(self, content: str) -> dict:
        warnings = []
        project = self._extract_first_match(
            content,
            [
                r"Projeto recomendado\s*\n+(.+)",
                r"Projeto:\s*(.+)",
                r"Projeto recomendado:\s*(.+)",
            ],
        )
        theme = self._extract_first_match(
            content,
            [
                r"Tema central da semana\s*\n+(.+)",
                r"Tema central:\s*(.+)",
                r"Tema:\s*(.+)",
            ],
        )
        frequency = self._extract_first_match(content, [r"Frequ[eê]ncia:\s*(.+)"])

        if not project:
            project = "Projeto a definir"
            warnings.append("Projeto não encontrado no briefing; usando fallback seguro.")
        if not theme:
            theme = "Tema a definir a partir do briefing aprovado"
            warnings.append("Tema central não encontrado no briefing; usando fallback seguro.")
        if not frequency:
            frequency = "Segunda / Quarta / Sexta"

        return {
            "project": self._clean_metadata_value(project),
            "theme": self._clean_metadata_value(theme),
            "frequency": self._clean_metadata_value(frequency),
            "warnings": warnings,
        }

    def _extract_recommendation_id(self, content: str) -> str | None:
        match = re.search(r"Recommendation ID:\s*(.*)", content, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            return value or None
        return None

    def _extract_first_match(self, content: str, patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _clean_metadata_value(self, value: str) -> str:
        value = re.sub(r"^[#>\-\s]+", "", value or "").strip()
        return value.split("\n")[0].strip()

    def _mark_briefing_generated(self, filename: str, folder_name: str) -> None:
        file_path = self._briefing_path(filename)
        if not os.path.exists(file_path):
            return

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        now = datetime.now(zoneinfo.ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%dT%H:%M:%S%z")
        content = re.sub(r"^(Status:\s*).*$", "Status: generated", content, flags=re.MULTILINE | re.IGNORECASE)
        content += f"\n\n---\n\nGenerated folder: {folder_name}\nSemana gerada em: {now}\n"

        backup_path = file_path + ".bak"
        shutil.copy2(file_path, backup_path)
        fd, temp_path = tempfile.mkstemp(dir=self.briefings_dir, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tf:
                tf.write(content)
            os.replace(temp_path, file_path)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            shutil.copy2(backup_path, file_path)
            raise

    def _briefing_path(self, filename: str) -> str:
        return os.path.join(self.briefings_dir, os.path.basename(filename))
