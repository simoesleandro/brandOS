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
                history = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid publication-log.json: {json_path}") from e
        except OSError as e:
            raise ValueError(f"Could not read publication-log.json: {json_path}") from e

        self._validate_history(history)
        return history
            
    def save(self, history: list) -> None:
        import tempfile
        import shutil
        import datetime
        json_path = os.path.join(self.registry_dir, "publication-log.json")

        self._validate_history(history)
        
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
        self._validate_history(history)
        md_path = os.path.join(self.registry_dir, "publication-log.md")
        md_content = "# Publication Log\n\n| Data | Projeto | Status Geral |\n|---|---|---|\n"
        for entry in history:
            md_content += f"| {entry.get('date', '')} | {entry.get('project', '')} | {entry.get('status', '')} |\n"
            
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    def iter_items(self, history: list | None = None):
        """Yield (entry, item) pairs from the canonical nested week registry."""
        entries = self.load() if history is None else history
        self._validate_history(entries)

        for entry in entries:
            for item in entry.get("items", []):
                yield entry, item

    def find_item(self, item_id: str, history: list | None = None):
        """Find an item by item_id or legacy id and return (entry, item)."""
        if not item_id:
            return None, None

        for entry, item in self.iter_items(history):
            if self.get_item_identifier(item) == item_id:
                return entry, item
        return None, None

    def preview_invalid_items(self, history: list | None = None) -> list:
        """Return root-level loose items or malformed entries that need cleanup."""
        entries = self.load() if history is None else history
        if not isinstance(entries, list):
            return [{"index": None, "reason": "Registry root is not a list"}]

        suspects = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                suspects.append({"index": index, "reason": "Entry is not an object"})
                continue

            if "items" not in entry and self._looks_like_item(entry):
                suspects.append({
                    "index": index,
                    "identifier": self.get_item_identifier(entry),
                    "title": entry.get("title"),
                    "status": entry.get("status"),
                    "reason": "Loose item at registry root"
                })

        return suspects

    @staticmethod
    def get_item_identifier(item: dict) -> str | None:
        return item.get("item_id") or item.get("id")

    def _validate_history(self, history: list) -> None:
        if not isinstance(history, list):
            raise ValueError("publication-log.json must be a list of week entries.")

        for index, entry in enumerate(history):
            if not isinstance(entry, dict):
                raise ValueError(f"publication-log entry {index} must be an object.")
            if "items" in entry and not isinstance(entry["items"], list):
                raise ValueError(f"publication-log entry {index} has a non-list items field.")

    def _looks_like_item(self, entry: dict) -> bool:
        return any(key in entry for key in ("item_id", "content_file", "linked_to_item_id", "asset_role"))
