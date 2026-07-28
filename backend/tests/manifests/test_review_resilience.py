from unittest.mock import AsyncMock

import pytest

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
