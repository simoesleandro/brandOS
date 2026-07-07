import json
import os


def test_briefing_service_lists_and_reads_briefings(briefing_service):
    briefings = briefing_service.list_briefings()

    assert len(briefings) == 2
    assert briefings[0]["filename"] in {"briefing-001.md", "briefing-002.md"}

    content = briefing_service.read_briefing("briefing-001.md")
    assert "Status: briefing_aprovado" in content


def test_briefing_service_blocks_path_traversal(briefing_service):
    content = briefing_service.read_briefing("../briefing-001.md")
    assert "Status: briefing_aprovado" in content


def test_briefing_service_prepare_week_defaults(briefing_service):
    defaults = briefing_service.prepare_week_from_briefing("briefing-001.md")

    assert defaults["projeto"] == "Projeto a definir"
    assert defaults["tema_central"] == "Tema a definir a partir do briefing aprovado"
    assert defaults["canal"] == "LinkedIn"
    assert defaults["quantidade_posts"] == 3
    assert defaults["data_inicial"]
    assert defaults["warnings"]


def test_briefing_service_prepare_week_extracts_metadata(briefing_service):
    briefing_service.edit_briefing(
        "briefing-001.md",
        "Status: briefing_aprovado\nProjeto: BrandOS\nTema central: Operacao editorial com IA\nFrequencia: Segunda / Quarta / Sexta\n\n# Briefing",
        True,
    )

    data = briefing_service.prepare_week_from_briefing("briefing-001.md")

    assert data["projeto"] == "BrandOS"
    assert data["tema_central"] == "Operacao editorial com IA"
    assert data["warnings"] == []


def test_briefing_service_edit_and_approve_briefing(briefing_service):
    edit_result = briefing_service.edit_briefing(
        "briefing-002.md",
        "Data de criação: 2026-07-03\nFonte: Teste\nStatus: draft\n\n## Conteudo\nEditado",
        True,
    )

    assert edit_result["status"] == "success"

    approve_result = briefing_service.approve_briefing("briefing-002.md", True, "Tester")
    assert approve_result["status"] == "success"

    content = briefing_service.read_briefing("briefing-002.md")
    assert "Status: approved" in content
    assert "Aprovado por: Tester" in content


def test_briefing_service_archive_briefing(briefing_service):
    briefing_service.edit_briefing(
        "briefing-002.md",
        "Data de criação: 2026-07-03\nFonte: Teste\nStatus: reviewed\n\n## Conteudo\nPara arquivar",
        True,
    )

    result = briefing_service.archive_briefing("briefing-002.md", True, "Tester")

    assert result["status"] == "success"
    content = briefing_service.read_briefing("briefing-002.md")
    assert "Status: archived" in content
    assert "Arquivado por: Tester" in content


def test_briefing_service_create_from_cmo_recommendation(briefing_service, mock_env):
    cmo_dir = os.path.join(mock_env, "data", "generated", "cmo-recommendations")
    os.makedirs(cmo_dir, exist_ok=True)

    recommendation_file = os.path.join(cmo_dir, "rec-001.md")
    with open(recommendation_file, "w", encoding="utf-8") as f:
        f.write(
            "# Rec\n\n"
            "## 1. Diagnóstico rápido\nDiagnóstico.\n\n"
            "## 2. O que aprendemos até agora\nAprendizado.\n\n"
            "## 3. Briefing recomendado para aprovação humana\nObjetivo.\n\n"
            "## 4. Temas recomendados para a próxima semana\nTemas.\n\n"
            "## 5. Formatos recomendados\nFormatos.\n\n"
            "## 6. Sugestão de agenda semanal\nAgenda.\n\n"
            "## 7. O que continuar\nContinuar.\n\n"
            "## 8. O que evitar\nEvitar.\n\n"
            "## 9. Riscos e cuidados\nRiscos.\n"
        )

    index_path = os.path.join(cmo_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({
            "recommendations": [
                {"id": "rec-001", "file": "data/generated/cmo-recommendations/rec-001.md"}
            ]
        }, f)

    result = briefing_service.create_briefing_from_cmo_recommendation("rec-001", True, "Nota humana")

    assert result["status"] == "success"
    assert result["recommendation_id"] == "rec-001"
    created_path = os.path.join(mock_env, result["briefing_file"])
    assert os.path.exists(created_path)
    with open(created_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Recommendation ID: rec-001" in content
    assert "Nota humana" in content


def test_briefing_service_generate_week_uses_unified_workflow(monkeypatch, briefing_service):
    captured = {}

    def fake_run_weekly_workflow(base_dir, request, llm_client=None):
        captured["base_dir"] = base_dir
        captured["request"] = request
        return {
            "status": "success",
            "folder": "2026-07-13-semana-brandos",
            "files": ["01-diagnostico-cmo.md"],
            "item_ids": ["post-segunda"],
            "warnings": [],
        }

    monkeypatch.setattr("app.core.services.briefing_service.run_weekly_workflow", fake_run_weekly_workflow)
    briefing_service.edit_briefing(
        "briefing-001.md",
        "Status: briefing_aprovado\nProjeto: BrandOS\nTema central: Operacao editorial\nRecommendation ID: rec-001\n\n# Briefing",
        True,
    )

    result = briefing_service.generate_week_from_briefing(
        "briefing-001.md",
        {"start_date": "2026-07-13", "frequencia": "Segunda / Quarta / Sexta"},
    )

    assert result["status"] == "success"
    assert captured["request"].project == "BrandOS"
    assert captured["request"].theme == "Operacao editorial"
    assert captured["request"].source_recommendation_id == "rec-001"

    content = briefing_service.read_briefing("briefing-001.md")
    assert "Status: generated" in content
    assert "Generated folder: 2026-07-13-semana-brandos" in content
