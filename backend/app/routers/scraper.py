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


@router.post("/recache")
async def recache_resources(
    current_user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
    overwrite: bool = False,
    max_concurrent: int = 5,
):
    """
    Re-cache all existing resources without re-scraping.
    
    Downloads all resources currently in Redis to local cache.
    
    Query parameters:
    - overwrite: If True, overwrite existing cached files. If False, skip already cached files.
    - max_concurrent: Maximum concurrent downloads (default: 5)
    
    Requires authentication.
    """
    from app.services import cache_service
    from app.core.log_broadcaster import broadcaster, LogLevel
    
    settings = await setting_service.get_all_settings(db)
    
    async def run_recache():
        await broadcaster.broadcast(
            f"📥 Starting re-cache job (overwrite={overwrite}, concurrent={max_concurrent})...",
            level=LogLevel.INFO,
        )
        
        async def progress_callback(downloaded, skipped, failed, total):
            if (downloaded + skipped + failed) % 20 == 0:
                await broadcaster.broadcast(
                    f"📦 Progress: {downloaded} downloaded, {skipped} skipped, {failed} failed / {total}",
                    level=LogLevel.INFO,
                )
        
        stats = await cache_service.recache_all_resources(
            settings=settings,
            skip_existing=not overwrite,
            max_concurrent=max_concurrent,
            progress_callback=progress_callback,
        )
        
        await broadcaster.broadcast(
            f"✅ Re-cache completed: {stats['downloaded']} downloaded, {stats['skipped']} skipped, {stats['failed']} failed / {stats['total']}",
            level=LogLevel.SUCCESS if stats['failed'] == 0 else LogLevel.WARNING,
        )
    
    background_tasks.add_task(run_recache)
    
    return {
        "message": "Re-cache job started in background",
        "overwrite": overwrite,
        "max_concurrent": max_concurrent,
    }


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


# WebSocket endpoint for real-time log streaming
from fastapi import WebSocket, WebSocketDisconnect, Query
from app.core.security import decode_access_token
from app.core.log_broadcaster import broadcaster


@router.websocket("/ws/logs")
async def websocket_logs(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint for real-time scraper log streaming.
    
    Connect with: ws://host/api/scraper/ws/logs?token=<jwt_token>
    
    Messages are JSON with format:
    {
        "level": "info|success|warning|error",
        "message": "Log message text",
        "scraper": "scraper_name or null",
        "timestamp": "ISO timestamp"
    }
    """
    # Validate JWT token
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
    
    # Accept the connection
    await websocket.accept()
    
    # Subscribe to log broadcaster
    queue = await broadcaster.subscribe()
    
    try:
        # Send welcome message
        await websocket.send_json({
            "level": "info",
            "message": "Connected to log stream",
            "scraper": None,
            "timestamp": None,
        })
        
        # Forward messages from queue to WebSocket
        while True:
            try:
                # Wait for messages with timeout for keepalive
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(message)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await broadcaster.unsubscribe(queue)


import asyncio

