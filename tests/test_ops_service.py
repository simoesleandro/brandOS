def test_ops_service_normalizes_missing_item_ids(ops_service):
    result = ops_service.normalize_registry_item_ids()

    assert result["normalized_count"] == 3
    assert "post-segunda" in result["normalized_items"]
    assert "post-quarta" in result["normalized_items"]
    assert "carrossel" in result["normalized_items"]

    history = ops_service.history_repo.load()
    assert history[0]["items"][0]["item_id"] == "post-segunda"


def test_ops_service_preview_invalid_items(ops_service):
    history = ops_service.history_repo.load()
    history[0]["items"].append({"id": "bad", "title": "Test Bad", "status": "generated"})
    ops_service.history_repo.save(history)

    result = ops_service.preview_invalid_items()

    assert any(
        any("Contém 'Test'" in reason for reason in suspect["reasons"])
        for suspect in result["suspects"]
    )


def test_ops_service_discard_items_bulk_skips_published_and_assets(ops_service):
    result = ops_service.discard_items_bulk(
        ["post-segunda", "post-quarta", "carrossel"],
        "Limpeza bulk",
        True,
    )

    assert result["discarded_count"] == 1

    history = ops_service.history_repo.load()
    assert history[0]["items"][0]["status"] == "published"
    assert history[1]["items"][0]["status"] == "discarded"
    assert history[1]["items"][1]["status"] == "used_as_asset"


def test_ops_service_dashboard_metrics_counts_main_posts_and_assets(ops_service):
    metrics = ops_service.get_dashboard_metrics()

    assert metrics["total_weeks"] == 2
    assert metrics["total_items"] == 2
    assert metrics["published_items"] == 1
    assert metrics["pending_items"] == 1
    assert metrics["linked_assets_items"] == 1


def test_ops_service_get_ops_dashboard_groups_pipeline(ops_service):
    dashboard = ops_service.get_ops_dashboard()

    assert dashboard["error"] is None
    assert dashboard["counts"]["total_main_posts"] == 2
    assert dashboard["counts"]["published_count"] == 1
    assert dashboard["pipeline_groups"]["published"][0]["identifier"] == "post-segunda"
    assert dashboard["lists"]["ignored_items"][0]["item"]["id"] == "carrossel"
