from collections import defaultdict

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.web.dependencies import get_brandos_service
from app.web.templates_env import templates

router = APIRouter(prefix="/projects", tags=["projects"])
service = get_brandos_service()


PUBLISHED_STATUSES = {"published", "completed"}
READY_STATUSES = {"approved", "ready_to_publish", "publishing_ready", "scheduled"}


def _clean(value: object, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _project_key(value: object) -> str:
    return _clean(value, "Sem projeto").lower()


def _status_for_project(posts: list[dict]) -> dict:
    if not posts:
        return {
            "label": "Sem narrativa",
            "tone": "quiet",
            "hint": "Ainda não existe post principal associado a este projeto.",
        }
    if any(post["status"] in READY_STATUSES for post in posts):
        return {
            "label": "Pronto para publicar",
            "tone": "ready",
            "hint": "Há conteúdo revisável ou publicável para este projeto.",
        }
    if any(post["status"] in PUBLISHED_STATUSES for post in posts):
        return {
            "label": "Autoridade ativa",
            "tone": "published",
            "hint": "Este projeto já sustenta presença pública no LinkedIn.",
        }
    return {
        "label": "Em produção",
        "tone": "draft",
        "hint": "Existe conteúdo, mas ainda precisa de revisão ou publicação.",
    }


def _posts_by_project() -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for entry in service.list_history():
        folder_id = entry.get("id") or entry.get("date") or ""
        entry_project = entry.get("project") or "Sem projeto"
        for item in entry.get("items", []):
            is_main_publication, _ = service._is_main_publication(item)
            if not is_main_publication:
                continue
            project_name = item.get("project") or entry_project
            item_id = service._get_item_identifier(item)
            grouped[_project_key(project_name)].append(
                {
                    "title": _clean(item.get("title") or item.get("file") or item_id, "Post sem titulo"),
                    "status": _clean(item.get("status"), "draft").lower(),
                    "url": f"/publications/{folder_id}/item/{item_id}" if folder_id and item_id else "/publications",
                }
            )
    return grouped


def _build_project_cards(projects: list[dict]) -> list[dict]:
    grouped_posts = _posts_by_project()
    cards = []
    for index, project in enumerate(projects):
        name = _clean(project.get("name"), "Projeto sem nome")
        posts = grouped_posts.get(_project_key(name), [])
        cards.append(
            {
                "index": index,
                "name": name,
                "github": project.get("github") or "",
                "site_demo": project.get("site/demo") or "",
                "status": project.get("status") or "",
                "categoria": project.get("categoria") or "",
                "descricao_curta": project.get("descricao_curta") or "",
                "descricao_editorial": project.get("descricao_editorial") or "",
                "regras_linguagem": project.get("regras_linguagem") or "",
                "prioridade_conteudo": project.get("prioridade_conteudo") or project.get("prioridade") or "",
                "visual_recomendado": project.get("visual_recomendado") or "",
                "posts": posts[:3],
                "posts_count": len(posts),
                "published_count": sum(1 for post in posts if post["status"] in PUBLISHED_STATUSES),
                "ready_count": sum(1 for post in posts if post["status"] in READY_STATUSES),
                "narrative": _status_for_project(posts),
            }
        )
    return cards


@router.get("/")
async def get_projects(request: Request):
    projects = service.get_projects_list()
    project_cards = _build_project_cards(projects)
    stats = {
        "total": len(project_cards),
        "with_links": sum(
            1
            for project in project_cards
            if project["github"] and project["github"] != "link não cadastrado"
        ),
        "silent": sum(1 for project in project_cards if project["posts_count"] == 0),
        "published": sum(1 for project in project_cards if project["published_count"] > 0),
    }
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "projects": project_cards,
        "stats": stats,
    })


@router.post("/{project_index}/update")
async def update_project(
    project_index: int,
    name: str = Form(...),
    github: str = Form(""),
    site_demo: str = Form(""),
    status: str = Form(""),
    categoria: str = Form(""),
    descricao_curta: str = Form(""),
    descricao_editorial: str = Form(""),
    regras_linguagem: str = Form(""),
    prioridade_conteudo: str = Form(""),
    visual_recomendado: str = Form(""),
):
    try:
        service.update_project_profile(
            project_index,
            {
                "name": name,
                "github": github,
                "site/demo": site_demo,
                "status": status,
                "categoria": categoria,
                "descricao_curta": descricao_curta,
                "descricao_editorial": descricao_editorial,
                "regras_linguagem": regras_linguagem,
                "prioridade_conteudo": prioridade_conteudo,
                "visual_recomendado": visual_recomendado,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RedirectResponse(url="/projects?msg=project_saved", status_code=303)
