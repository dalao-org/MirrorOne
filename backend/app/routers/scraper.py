"""
Scraper router for managing scrape tasks.
"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from sqlalchemy import select, desc

from app.core.dependencies import DbSession, CurrentUser
from app.schemas.scrape_log import ScrapeLogResponse, ScrapeLogListResponse, ScraperStatusResponse
from app.models.scrape_log import ScrapeLog
from app.services import setting_service
from app import redis_client

router = APIRouter(prefix="/api/scraper", tags=["Scraper"])


@router.get("/status", response_model=ScraperStatusResponse)
async def get_scraper_status(current_user: CurrentUser, db: DbSession):
    """
    Get scheduler and scraper status.
    
    Requires authentication.
    """
    settings = await setting_service.get_all_settings(db)
    scheduler_times = await redis_client.get_scheduler_times()
    
    # Get available scrapers from registry
    # Import here to avoid circular imports
    from app.scrapers.registry import registry
    
    return ScraperStatusResponse(
        enabled=settings.get("enable_auto_scrape", True),
        interval_hours=settings.get("scrape_interval_hours", 6),
        last_run=scheduler_times.get("last_run"),
        next_run=scheduler_times.get("next_run"),
        available_scrapers=registry.get_all_names(),
    )


@router.post("/run")
async def run_all_scrapers(
    current_user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
):
    """
    Trigger a full scrape of all sources.
    
    Runs in the background. Check logs for results.
    Requires authentication.
    """
    from app.scheduler.jobs import run_scrape_job
    
    settings = await setting_service.get_all_settings(db)
    background_tasks.add_task(run_scrape_job, settings)
    
    return {"message": "Scrape job started in background"}


@router.post("/run/{scraper_name}")
async def run_single_scraper(
    scraper_name: str,
    current_user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
):
    """
    Trigger a single scraper.
    
    Runs in the background. Check logs for results.
    Requires authentication.
    """
    from app.scrapers.registry import registry
    
    if scraper_name not in registry.get_all_names():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scraper '{scraper_name}' not found",
        )
    
    from app.scheduler.jobs import run_single_scraper_job
    
    settings = await setting_service.get_all_settings(db)
    background_tasks.add_task(run_single_scraper_job, scraper_name, settings)
    
    return {"message": f"Scraper '{scraper_name}' started in background"}


@router.get("/logs", response_model=ScrapeLogListResponse)
async def get_scrape_logs(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = 50,
    offset: int = 0,
):
    """
    Get scrape execution logs.
    
    Requires authentication.
    """
    result = await db.execute(
        select(ScrapeLog)
        .order_by(desc(ScrapeLog.started_at))
        .limit(limit)
        .offset(offset)
    )
    logs = result.scalars().all()
    
    # Get total count
    count_result = await db.execute(select(ScrapeLog))
    total = len(count_result.scalars().all())
    
    return ScrapeLogListResponse(
        total=total,
        logs=[ScrapeLogResponse.model_validate(log) for log in logs],
    )
