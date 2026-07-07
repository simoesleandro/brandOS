import os


def test_publication_service_discards_item(publication_service):
    result = publication_service.discard_item("post-quarta", "Motivo direto", True)

    assert result["status"] == "success"

    history = publication_service.history_repo.load()
    item = history[1]["items"][0]

    assert item["id"] == "post-quarta"
    assert item["status"] == "discarded"
    assert item["discard_reason"] == "Motivo direto"
    assert item["discard_history"][0]["reason"] == "Motivo direto"


def test_publication_service_blocks_asset_discard(publication_service):
    try:
        publication_service.discard_item("carrossel", "Nao pode", True)
    except ValueError as exc:
        assert "Assets vinculados" in str(exc)
    else:
        raise AssertionError("Expected ValueError for linked asset discard")


def test_publication_service_update_content_creates_backup(publication_service, mock_env):
    history = publication_service.history_repo.load()
    item = history[1]["items"][0]
    item["content_file"] = "data/generated/2026-01-08-semana-fake2/04-post-quarta.md"
    item["status"] = "generated"
    publication_service.history_repo.save(history)

    result = publication_service.update_item_content("post-quarta", "Conteudo refinado", "Teste direto")

    assert result["status"] == "success"
    assert result["new_status"] == "edited"

    content_path = os.path.join(mock_env, "data", "generated", "2026-01-08-semana-fake2", "04-post-quarta.md")
    with open(content_path, "r", encoding="utf-8") as f:
        assert f.read() == "Conteudo refinado"

    backup_path = os.path.join(mock_env, result["backup_file"])
    assert os.path.exists(backup_path)


def test_publication_service_mark_manual_published(publication_service):
    result = publication_service.mark_manual_published("post-quarta", {"published_url": "https://linkedin.com/posts/123"})

    assert result["status"] == "published"
    assert result["published_url"] == "https://linkedin.com/posts/123"
    assert result["publication_history"][-1]["event"] == "manual_mark_published"


def test_publication_service_starts_and_updates_post_publish_tracking(publication_service):
    start = publication_service.start_post_publish_tracking("post-segunda", True)

    assert start["status"] == "success"

    updated = publication_service.update_post_publish_tracking_status("post-segunda", "completed", True)
    assert updated["status"] == "success"

    history = publication_service.history_repo.load()
    item = history[0]["items"][0]
    assert item["post_publish_tracking_status"] == "completed"
    assert "post_publish_completed_at" in item
