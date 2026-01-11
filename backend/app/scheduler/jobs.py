"""
Scheduler jobs for periodic scraping.
"""
import logging
from datetime import datetime, timedelta, UTC
from typing import Any

from app import redis_client
from app.scrapers.registry import registry
from app.scrapers.base import ScrapeResult
from app.database import get_db_session
from app.models.scrape_log import ScrapeLog

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


async def update_redis_from_result(result: ScrapeResult) -> None:
    """
    Update Redis with resources from a scrape result.
    
    Args:
        result: ScrapeResult with resources and version metas
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


async def run_scrape_job(settings: dict[str, Any]) -> list[ScrapeResult]:
    """
    Run all scrapers and update Redis.
    
    Args:
        settings: Settings dictionary
        
    Returns:
        List of ScrapeResults
    """
    logger.info("Starting scheduled scrape job")
    
    # Update scheduler times
    now = datetime.now(UTC)
    interval_hours = settings.get("scrape_interval_hours", 6)
    next_run = now + timedelta(hours=interval_hours)
    await redis_client.set_scheduler_times(last_run=now, next_run=next_run)
    
    # Run all scrapers
    results = await registry.run_all(settings)
    
    # Process results
    for result in results:
        logger.info(
            f"Scraper '{result.scraper_name}' completed: "
            f"status={result.status}, resources={result.resources_count}, "
            f"duration={result.duration_seconds:.2f}s"
        )
        
        # Update Redis
        await update_redis_from_result(result)
        
        # Save log
        await save_scrape_log(result)
    
    logger.info(f"Scheduled scrape job completed. {len(results)} scrapers processed.")
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
    
    result = await registry.run_one(scraper_name, settings)
    
    if result is None:
        logger.error(f"Scraper '{scraper_name}' not found")
        return None
    
    logger.info(
        f"Scraper '{result.scraper_name}' completed: "
        f"status={result.status}, resources={result.resources_count}, "
        f"duration={result.duration_seconds:.2f}s"
    )
    
    # Update Redis
    await update_redis_from_result(result)
    
    # Save log
    await save_scrape_log(result)
    
    return result
