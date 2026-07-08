from collections import defaultdict

from fastapi import APIRouter, Request

from app.web.dependencies import get_brandos_service
from app.web.templates_env import templates


router = APIRouter(prefix="/authority", tags=["authority"])
service = get_brandos_service()

PUBLISHED_STATUSES = {"published", "completed"}
READY_STATUSES = {"approved", "ready_to_publish", "publishing_ready", "scheduled"}


def _clean(value: object, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _normalise_project_name(value: object) -> str:
    return _clean(value, "Sem projeto").lower()


def _item_status(item: dict) -> str:
    return _clean(item.get("status"), "draft").lower()


def _project_links(project: dict) -> dict:
    return {
        "github": project.get("github") or "",
        "site": project.get("site/demo") or project.get("site") or project.get("demo") or "",
    }


@router.get("/")
async def get_authority(request: Request):
    projects = service.get_projects_list()
    history = service.list_history()
    posts_by_project = defaultdict(list)

    for entry in history:
        folder_id = entry.get("id") or entry.get("date") or ""
        entry_project = entry.get("project") or "Sem projeto"

        for item in entry.get("items", []):
            is_main_publication, _ = service._is_main_publication(item)
            if not is_main_publication:
                continue

            project_name = _clean(item.get("project") or entry_project, "Sem projeto")
            item_id = service._get_item_identifier(item)
            status = _item_status(item)
            posts_by_project[_normalise_project_name(project_name)].append(
                {
                    "title": _clean(item.get("title") or item.get("file") or item_id, "Post sem titulo"),
                    "status": status,
                    "date": item.get("scheduled_date") or item.get("published_at") or entry.get("date") or "",
                    "url": f"/publications/{folder_id}/item/{item_id}" if folder_id and item_id else "/publications",
                }
            )

    project_cards = []
    known_project_keys = set()

    for project in projects:
        name = _clean(project.get("name"), "Projeto sem nome")
        project_key = _normalise_project_name(name)
        known_project_keys.add(project_key)
        posts = posts_by_project.get(project_key, [])
        project_cards.append(
            {
                "name": name,
                "category": project.get("categoria") or project.get("categoria/area") or "",
                "status": project.get("status") or "",
                "priority": project.get("prioridade") or "",
                "links": _project_links(project),
                "posts": posts[:4],
                "posts_count": len(posts),
                "published_count": sum(1 for post in posts if post["status"] in PUBLISHED_STATUSES),
                "ready_count": sum(1 for post in posts if post["status"] in READY_STATUSES),
                "gap": "Sem narrativa publica ainda" if not posts else "",
            }
        )

    for project_key, posts in sorted(posts_by_project.items()):
        if project_key in known_project_keys:
            continue
        project_cards.append(
            {
                "name": project_key.title(),
                "category": "Detectado no historico",
                "status": "",
                "priority": "",
                "links": {"github": "", "site": ""},
                "posts": posts[:4],
                "posts_count": len(posts),
                "published_count": sum(1 for post in posts if post["status"] in PUBLISHED_STATUSES),
                "ready_count": sum(1 for post in posts if post["status"] in READY_STATUSES),
                "gap": "",
            }
        )

    all_posts = [post for posts in posts_by_project.values() for post in posts]
    stats = {
        "projects": len(project_cards),
        "posts": len(all_posts),
        "published": sum(1 for post in all_posts if post["status"] in PUBLISHED_STATUSES),
        "ready": sum(1 for post in all_posts if post["status"] in READY_STATUSES),
        "silent_projects": sum(1 for project in project_cards if project["posts_count"] == 0),
    }

    pillars = [
        {
            "title": "Construção em publico",
            "description": "Mostre decisões, bastidores e evolução real dos seus projetos.",
        },
        {
            "title": "IA aplicada a produto",
            "description": "Transforme experimentos e agentes em aprendizados claros para o mercado.",
        },
        {
            "title": "Cases e provas",
            "description": "Use entregas, telas, métricas e antes/depois para sustentar autoridade.",
        },
        {
            "title": "Opinião editorial",
            "description": "Defenda critérios, boas práticas e pontos de vista que você quer ocupar.",
        },
    ]

    gaps = []
    if stats["silent_projects"]:
        gaps.append(f"{stats['silent_projects']} projeto(s) ainda nao viraram narrativa no LinkedIn.")
    if stats["ready"]:
        gaps.append(f"{stats['ready']} post(s) ja estao prontos para publicar.")
    if stats["posts"] == 0:
        gaps.append("Comece gerando uma recomendacao CMO para escolher o primeiro tema.")

    return templates.TemplateResponse(
        "authority.html",
        {
            "request": request,
            "stats": stats,
            "pillars": pillars,
            "project_cards": project_cards,
            "gaps": gaps,
        },
    )
