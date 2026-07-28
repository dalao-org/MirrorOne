from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app.main import _public_manifest_health
from app.manifests import service
from app.manifests.metrics import render_metrics, set_metric
from app.scheduler import jobs
from app.scrapers.base import ScrapeResult
from app.scrapers.php_plugins import PhpPluginsScraper
from app.services import redirect_service


@pytest.mark.asyncio
async def test_pecl_scraper_logs_package_failure_and_continues(monkeypatch):
    scraper = PhpPluginsScraper({}, AsyncMock())
    scrape_package = AsyncMock(side_effect=RuntimeError("parser failed"))
    log = AsyncMock()
    monkeypatch.setattr(
        "app.scrapers.php_plugins.PECL_PACKAGES",
        [("sample", "sample", "sample_ver", False)],
    )
    monkeypatch.setattr(scraper, "_scrape_pecl_package", scrape_package)
    monkeypatch.setattr(scraper, "log", log)

    result = await scraper.scrape()

    assert result.success is True
    log.assert_awaited_once()
    assert "sample" in log.await_args.args[0]
    assert "RuntimeError: parser failed" in log.await_args.args[0]


@pytest.mark.asyncio
async def test_metadata_lock_contention_degrades_without_writing(monkeypatch):
    async def lock_is_busy():
        raise RuntimeError("another artifact metadata update is already in progress")

    update = AsyncMock()
    broadcast = AsyncMock()
    monkeypatch.setattr(jobs.redis_client, "begin_manifest_metadata_update", lock_is_busy)
    monkeypatch.setattr(jobs, "update_redis_from_result", update)
    monkeypatch.setattr(jobs.broadcaster, "broadcast", broadcast)

    updated = await jobs._update_redis_with_manifest_lock(
        [ScrapeResult(scraper_name="sample", success=True)],
        {},
    )

    assert updated is False
    update.assert_not_awaited()
    broadcast.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_scraper_metadata_does_not_abort_later_results(monkeypatch):
    update = AsyncMock(side_effect=[ValueError("unsafe URL"), None])
    broadcast = AsyncMock()
    monkeypatch.setattr(
        jobs.redis_client,
        "begin_manifest_metadata_update",
        AsyncMock(return_value="token"),
    )
    monkeypatch.setattr(
        jobs.redis_client,
        "refresh_manifest_metadata_update",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        jobs.redis_client,
        "end_manifest_metadata_update",
        AsyncMock(),
    )
    monkeypatch.setattr(jobs, "update_redis_from_result", update)
    monkeypatch.setattr(jobs.broadcaster, "broadcast", broadcast)

    updated = await jobs._update_redis_with_manifest_lock(
        [
            ScrapeResult(scraper_name="broken", success=True),
            ScrapeResult(scraper_name="valid", success=True),
        ],
        {},
    )

    assert updated is False
    assert update.await_count == 2
    broadcast.assert_awaited_once()


def test_prometheus_metrics_preserve_timestamp_precision():
    timestamp = 1_785_000_123.125
    set_metric("mirrorone_manifest_last_success_timestamp", timestamp)
    assert (
        f"mirrorone_manifest_last_success_timestamp {timestamp!r}"
        in render_metrics()
    )


def test_public_health_hides_internal_manifest_error():
    projected = _public_manifest_health({
        "state": "degraded",
        "revision": "revision",
        "last_success": "2026-07-28T00:00:00Z",
        "last_error": "OSError: C:\\private\\manifest.json",
        "statistics": {"artifact_count": 1},
    })
    assert projected == {
        "state": "degraded",
        "revision": "revision",
        "last_success": "2026-07-28T00:00:00Z",
    }


@pytest.mark.asyncio
async def test_manifest_publication_runs_in_worker_thread(monkeypatch):
    statistics = {
        "artifact_count": 0,
        "with_upstream_checksum": 0,
        "without_upstream_checksum": 0,
        "cached": 0,
        "not_cached": 0,
        "conflict_count": 0,
    }
    manifest = SimpleNamespace(
        statistics=SimpleNamespace(model_dump=lambda: statistics),
        artifacts=[],
    )

    class Builder:
        def __init__(self, values):
            self.values = values

        async def build(self):
            return manifest

    publisher = SimpleNamespace(publish=Mock(return_value={
        "changed": True,
        "generated_at": "2026-07-28T00:00:00Z",
        "revision": "revision",
        "sha256": "a" * 64,
    }))
    calls = []

    async def immediate_to_thread(function, *args):
        calls.append(function)
        return function(*args)

    monkeypatch.setattr(service, "ManifestBuilder", Builder)
    monkeypatch.setattr(service, "get_publisher", lambda values: publisher)
    monkeypatch.setattr(service.asyncio, "to_thread", immediate_to_thread)
    monkeypatch.setattr(
        service.redis_client,
        "set_manifest_status",
        AsyncMock(),
    )

    result = await service.rebuild_manifest({"manifest_enabled": True})

    assert result["state"] == "healthy"
    assert calls == [publisher.publish]


@pytest.mark.asyncio
async def test_empty_manifest_recommendations_remain_the_snapshot_source(monkeypatch):
    class Publisher:
        def read_current(self):
            return {"version_recommendations": {}}

    redis_versions = AsyncMock(return_value={"php84_ver": "8.4.12"})
    monkeypatch.setattr(
        "app.manifests.service.get_publisher",
        lambda: Publisher(),
    )
    monkeypatch.setattr(
        redirect_service.redis_client,
        "get_all_version_metas",
        redis_versions,
    )

    assert await redirect_service.get_suggest_versions_content() == ""
    redis_versions.assert_not_awaited()
