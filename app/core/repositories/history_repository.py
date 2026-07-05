import os
import json

class HistoryRepository:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.registry_dir = os.path.join(base_dir, "data", "registry")
        os.makedirs(self.registry_dir, exist_ok=True)
        
    def load(self) -> list:
        json_path = os.path.join(self.registry_dir, "publication-log.json")
        if not os.path.exists(json_path):
            return []
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
            
    def save(self, history: list) -> None:
        import tempfile
        import shutil
        import datetime
        json_path = os.path.join(self.registry_dir, "publication-log.json")
        
        # Create backup if exists
        if os.path.exists(json_path):
            backups_dir = os.path.join(self.registry_dir, "backups")
            os.makedirs(backups_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_file = os.path.join(backups_dir, f"publication-log-{timestamp}.json")
            shutil.copy2(json_path, backup_file)
            
        temp_fd, temp_path = tempfile.mkstemp(dir=self.registry_dir, text=True)
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, json_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
            
        self.rebuild_markdown_log(history)

    def rebuild_markdown_log(self, history: list) -> None:
        md_path = os.path.join(self.registry_dir, "publication-log.md")
        md_content = "# Publication Log\n\n| Data | Projeto | Status Geral |\n|---|---|---|\n"
        for entry in history:
            md_content += f"| {entry.get('date', '')} | {entry.get('project', '')} | {entry.get('status', '')} |\n"
            
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
