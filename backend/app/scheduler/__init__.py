"""
Scheduler package for periodic task execution.
"""
import logging
from datetime import datetime, timedelta, UTC
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app import redis_client
from app.database import get_db_session
from app.services import setting_service

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def scheduled_scrape_task():
    """
    Scheduled task that runs all scrapers.
    
    This is called by APScheduler at the configured interval.
    """
    from app.scheduler.jobs import run_scrape_job
    
    logger.info("Scheduled scrape task triggered")
    
    # Get settings
    async with get_db_session() as db:
        settings = await setting_service.get_all_settings(db)
    
    # Check if auto-scrape is enabled
    if not settings.get("enable_auto_scrape", True):
        logger.info("Auto-scrape is disabled, skipping")
        return
    
    # Run the scrape job
    await run_scrape_job(settings)


def setup_scheduler(interval_hours: int = 6):
    """
    Configure and start the scheduler.
    
    Args:
        interval_hours: Hours between scrape runs
    """
    # Remove existing job if any
    if scheduler.get_job("scrape_job"):
        scheduler.remove_job("scrape_job")
    
    # Add the scrape job
    scheduler.add_job(
        scheduled_scrape_task,
        trigger=IntervalTrigger(hours=interval_hours),
        id="scrape_job",
        name="Periodic Scrape Job",
        replace_existing=True,
    )
    
    logger.info(f"Scheduler configured with {interval_hours} hour interval")


async def start_scheduler():
    """Start the scheduler."""
    # Get interval from settings
    async with get_db_session() as db:
        settings = await setting_service.get_all_settings(db)
    
    interval_hours = settings.get("scrape_interval_hours", 6)
    
    setup_scheduler(interval_hours)
    scheduler.start()
    
    # Update next run time in Redis
    next_run = datetime.now(UTC) + timedelta(hours=interval_hours)
    await redis_client.set_scheduler_times(next_run=next_run)
    
    logger.info("Scheduler started")


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
