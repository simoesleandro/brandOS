import json
from pathlib import Path

from fastapi import APIRouter, Request

from app.web.templates_env import templates

router = APIRouter(prefix="/assets", tags=["assets"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = PROJECT_ROOT / "data" / "assets"
GENERATED_DIR = PROJECT_ROOT / "data" / "generated"

ASSET_CATEGORIES = ("images", "slides", "pdf", "video", "prompts", "source", "analytics")
FILE_CATEGORIES = {"images", "slides", "pdf", "video", "source"}


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _file_url(generation_id: str, item_id: str, category: str, file_name: str) -> str | None:
    if category not in FILE_CATEGORIES:
        return None
    return f"/assets/{generation_id}/{item_id}/{category}/{file_name}"


def _normalize_file_entry(entry, generation_id: str, item_id: str, category: str) -> dict:
    if isinstance(entry, str):
        file_name = entry
        label = entry
    else:
        file_name = entry.get("file_name") or entry.get("filename") or Path(entry.get("path", "")).name
        label = entry.get("original_filename") or file_name

    return {
        "label": label,
        "file_name": file_name,
        "url": _file_url(generation_id, item_id, category, file_name) if file_name else None,
    }


def _asset_package_from_manifest(folder: Path) -> dict:
    manifest = _read_json(folder / "manifest.json")
    generation_id = manifest.get("generation_id") or ""
    item_id = manifest.get("item_id") or ""
    files = manifest.get("files", {})
    categories = {}
    total_files = 0
    prompt_count = 0

    for category in ASSET_CATEGORIES:
        raw_items = files.get(category, []) or []
        if category == "prompts":
            prompt_count = len(raw_items)
            categories[category] = [
                {
                    "title": item.get("title") or "Prompt salvo",
                    "content": item.get("content") or "",
                    "source": item.get("source") or "manual",
                }
                for item in raw_items
                if isinstance(item, dict)
            ]
        else:
            normalized = [
                _normalize_file_entry(item, generation_id, item_id, category)
                for item in raw_items
            ]
            total_files += len(normalized)
            categories[category] = normalized

    return {
        "folder": folder.name,
        "generation_id": generation_id,
        "item_id": item_id,
        "project": manifest.get("project") or "Projeto não informado",
        "title": manifest.get("title") or folder.name,
        "asset_type": manifest.get("asset_type") or "asset",
        "status": manifest.get("status") or "draft",
        "categories": categories,
        "total_files": total_files,
        "prompt_count": prompt_count,
    }


def _asset_package_from_folder(folder: Path) -> dict:
    categories = {}
    total_files = 0
    for category in ASSET_CATEGORIES:
        category_dir = folder / category
        items = []
        if category_dir.exists() and category_dir.is_dir():
            items = [
                {"label": path.name, "file_name": path.name, "url": None}
                for path in sorted(category_dir.iterdir())
                if path.is_file()
            ]
        categories[category] = items
        if category != "prompts":
            total_files += len(items)

    return {
        "folder": folder.name,
        "generation_id": "",
        "item_id": "",
        "project": "Projeto não informado",
        "title": folder.name,
        "asset_type": "asset",
        "status": "draft",
        "categories": categories,
        "total_files": total_files,
        "prompt_count": len(categories.get("prompts", [])),
    }


def _list_asset_packages() -> list[dict]:
    if not ASSETS_DIR.exists():
        return []

    packages = []
    for folder in sorted((p for p in ASSETS_DIR.iterdir() if p.is_dir()), reverse=True):
        if (folder / "manifest.json").exists():
            packages.append(_asset_package_from_manifest(folder))
        else:
            packages.append(_asset_package_from_folder(folder))
    return packages


def _list_recommended_prompts() -> list[dict]:
    if not GENERATED_DIR.exists():
        return []

    prompts = []
    for path in sorted(GENERATED_DIR.glob("*/*prompt*.md"), reverse=True):
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            content = ""
        prompts.append({
            "folder": path.parent.name,
            "file_name": path.name,
            "content": content[:1200],
        })
    return prompts


@router.get("/")
async def list_assets(request: Request):
    packages = _list_asset_packages()
    prompts = _list_recommended_prompts()
    totals = {
        "packages": len(packages),
        "files": sum(package["total_files"] for package in packages),
        "prompts": sum(package["prompt_count"] for package in packages) + len(prompts),
        "images": sum(len(package["categories"].get("images", [])) for package in packages),
    }
    return templates.TemplateResponse("assets_visuals.html", {
        "request": request,
        "active_menu": "/assets",
        "packages": packages,
        "recommended_prompts": prompts,
        "totals": totals,
    })
