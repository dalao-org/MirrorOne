"""
Scheduler jobs for periodic scraping.
"""
import logging
from datetime import datetime, timedelta, UTC
from typing import Any

import httpx

from app import redis_client
from app.scrapers.registry import registry
from app.scrapers.base import ScrapeResult
from app.database import get_db_session
from app.models.scrape_log import ScrapeLog
from app.core.log_broadcaster import broadcaster, LogLevel

logger = logging.getLogger(__name__)


async def save_scrape_log(result: ScrapeResult) -> None:
    """
    Save a scrape result to the database.
    
    Args:
        result: ScrapeResult to save
    """
    async with get_db_session() as db:
        log = ScrapeLog(
            scraper_name=result.scraper_name,
            status=result.status,
            resources_count=result.resources_count,
            error_message=result.error_message,
            duration_seconds=result.duration_seconds,
            started_at=result.started_at,
            finished_at=result.finished_at,
        )
        db.add(log)
        await db.commit()


async def update_redis_from_result(result: ScrapeResult, settings: dict[str, Any] | None = None) -> None:
    """
    Update Redis with resources from a scrape result.
    
    Args:
        result: ScrapeResult with resources and version metas
        settings: Optional settings for cache mode
    """
    if not result.success and not result.resources:
        return
    
    # Delete old rules from this source
    await redis_client.delete_redirect_rules_by_source(result.scraper_name)
    
    # Add new rules
    for resource in result.resources:
        await redis_client.set_redirect_rule(
            filename=resource.file_name,
            url=resource.url,
            version=resource.version,
            source=result.scraper_name,
        )
    
    # Update version metas
    for meta in result.version_metas:
        await redis_client.set_version_meta(meta.key, meta.version)


async def download_cache_for_result(result: ScrapeResult, settings: dict[str, Any]) -> None:
    """
    Download resources to cache for a scrape result (parallel).
    
    Called separately after scraping is complete.
    """
    if settings.get("mirror_type") != "cache":
        return
    
    from app.services import cache_service
    
    cache_path = cache_service.get_cache_path(settings)
    
    await broadcaster.broadcast(
        f"📥 Downloading {len(result.resources)} files (parallel) for {result.scraper_name}...",
        level=LogLevel.INFO,
        scraper=result.scraper_name,
    )
    
    # Convert resources to dicts for parallel download
    resources = [
        {"url": r.url, "file_name": r.file_name, "source": result.scraper_name}
        for r in result.resources
    ]
    
    async def progress_callback(downloaded, skipped, failed, total):
        if (downloaded + skipped + failed) % 10 == 0:  # Update every 10 files
            await broadcaster.broadcast(
                f"📦 {result.scraper_name}: {downloaded} downloaded, {skipped} skipped, {failed} failed / {total}",
                level=LogLevel.INFO,
                scraper=result.scraper_name,
            )
    
    stats = await cache_service.download_resources_parallel(
        resources=resources,
        cache_path=cache_path,
        skip_existing=True,
        max_concurrent=5,
        progress_callback=progress_callback,
    )
    
    await broadcaster.broadcast(
        f"📦 Cache complete: {stats['downloaded']} downloaded, {stats['skipped']} skipped, {stats['failed']} failed for {result.scraper_name}",
        level=LogLevel.SUCCESS if stats['failed'] == 0 else LogLevel.WARNING,
        scraper=result.scraper_name,
    )


async def run_scrape_job(settings: dict[str, Any]) -> list[ScrapeResult]:
    """
    Run all scrapers and update Redis.
    
    Args:
        settings: Settings dictionary
        
    Returns:
        List of ScrapeResults
    """
    logger.info("Starting scheduled scrape job")
    await broadcaster.broadcast(
        "🚀 Starting scheduled scrape job...",
        level=LogLevel.INFO,
    )
    
    # Update scheduler times
    now = datetime.now(UTC)
    interval_hours = settings.get("scrape_interval_hours", 6)
    next_run = now + timedelta(hours=interval_hours)
    await redis_client.set_scheduler_times(last_run=now, next_run=next_run)
    
    # Get scraper names for progress reporting
    scraper_names = registry.get_all_names()
    total_scrapers = len(scraper_names)
    
    await broadcaster.broadcast(
        f"📋 Found {total_scrapers} scrapers to run: {', '.join(scraper_names)}",
        level=LogLevel.INFO,
    )
    
    # Run all scrapers
    results = await registry.run_all(settings)
    
    # Process results
    success_count = 0
    failed_count = 0
    total_resources = 0
    
    for result in results:
        log_msg = (
            f"Scraper '{result.scraper_name}' completed: "
            f"status={result.status}, resources={result.resources_count}, "
            f"duration={result.duration_seconds:.2f}s"
        )
        logger.info(log_msg)
        
        # Broadcast result based on status
        if result.status == "success":
            success_count += 1
            total_resources += result.resources_count
            await broadcaster.broadcast(
                f"✅ {result.scraper_name}: {result.resources_count} resources ({result.duration_seconds:.1f}s)",
                level=LogLevel.SUCCESS,
                scraper=result.scraper_name,
            )
        elif result.status == "partial":
            success_count += 1
            total_resources += result.resources_count
            await broadcaster.broadcast(
                f"⚠️ {result.scraper_name}: {result.resources_count} resources (partial, {result.duration_seconds:.1f}s)",
                level=LogLevel.WARNING,
                scraper=result.scraper_name,
            )
        else:
            failed_count += 1
            error_msg = result.error_message or "Unknown error"
            await broadcaster.broadcast(
                f"❌ {result.scraper_name}: Failed - {error_msg}",
                level=LogLevel.ERROR,
                scraper=result.scraper_name,
            )
        
        # Update Redis
        await update_redis_from_result(result, settings)
        
        # Save log
        await save_scrape_log(result)
    
    # Final summary
    summary_msg = f"🏁 Scrape job completed: {success_count} succeeded, {failed_count} failed, {total_resources} total resources"
    logger.info(summary_msg)
    await broadcaster.broadcast(
        summary_msg,
        level=LogLevel.SUCCESS if failed_count == 0 else LogLevel.WARNING,
    )
    
    # Phase 2: Download files to cache (if cache mode enabled)
    if settings.get("mirror_type") == "cache":
        await broadcaster.broadcast(
            "📥 Starting cache download phase...",
            level=LogLevel.INFO,
        )
        for result in results:
            if result.success and result.resources:
                await download_cache_for_result(result, settings)
        await broadcaster.broadcast(
            "✅ Cache download phase completed",
            level=LogLevel.SUCCESS,
        )
    
    return results


async def run_single_scraper_job(scraper_name: str, settings: dict[str, Any]) -> ScrapeResult | None:
    """
    Run a single scraper and update Redis.
    
    Args:
        scraper_name: Name of the scraper to run
        settings: Settings dictionary
        
    Returns:
        ScrapeResult or None if scraper not found
    """
    logger.info(f"Starting single scraper job: {scraper_name}")
    await broadcaster.broadcast(
        f"🚀 Starting scraper: {scraper_name}",
        level=LogLevel.INFO,
        scraper=scraper_name,
    )
    
    result = await registry.run_one(scraper_name, settings)
    
    if result is None:
        logger.error(f"Scraper '{scraper_name}' not found")
        await broadcaster.broadcast(
            f"❌ Scraper '{scraper_name}' not found",
            level=LogLevel.ERROR,
            scraper=scraper_name,
        )
        return None
    
    log_msg = (
        f"Scraper '{result.scraper_name}' completed: "
        f"status={result.status}, resources={result.resources_count}, "
        f"duration={result.duration_seconds:.2f}s"
    )
    logger.info(log_msg)
    
    # Broadcast result based on status
    if result.status == "success":
        await broadcaster.broadcast(
            f"✅ {result.scraper_name}: {result.resources_count} resources ({result.duration_seconds:.1f}s)",
            level=LogLevel.SUCCESS,
            scraper=result.scraper_name,
        )
    elif result.status == "partial":
        await broadcaster.broadcast(
            f"⚠️ {result.scraper_name}: {result.resources_count} resources (partial)",
            level=LogLevel.WARNING,
            scraper=result.scraper_name,
        )
    else:
        error_msg = result.error_message or "Unknown error"
        await broadcaster.broadcast(
            f"❌ {result.scraper_name}: Failed - {error_msg}",
            level=LogLevel.ERROR,
            scraper=result.scraper_name,
        )
    
    # Update Redis
    await update_redis_from_result(result, settings)
    
    # Save log
    await save_scrape_log(result)
    
    return result
