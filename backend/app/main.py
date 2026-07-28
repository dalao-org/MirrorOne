"""
FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import close_db, get_db_session, init_db
from app.redis_client import close_redis, get_redis, migrate_redis_schema
from app.routers import (
    auth_router,
    manifests_router,
    redirect_router,
    resources_router,
    scraper_router,
    settings_router,
)
from app.scheduler import start_scheduler, stop_scheduler
from app.services import auth_service, setting_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting application...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize Redis connection
    await get_redis()
    logger.info("Redis connection established")
    
    await migrate_redis_schema()
    logger.info("Redis schema migration complete")

    database_settings = {}
    # Create admin user if not exists
    async with get_db_session() as db:
        existing_admin = await auth_service.get_user_by_username(db, settings.ADMIN_USERNAME)
        if existing_admin is None and settings.ADMIN_PASSWORD:
            await auth_service.create_admin_user(
                db,
                settings.ADMIN_USERNAME,
                settings.ADMIN_PASSWORD,
            )
            logger.info(f"Admin user '{settings.ADMIN_USERNAME}' created")
        
        # Initialize default settings
        await setting_service.init_default_settings(db)
        logger.info("Default settings initialized")
        database_settings = await setting_service.get_all_settings(db)

    from app.manifests.service import rebuild_manifest
    manifest_status = await rebuild_manifest(database_settings)
    if manifest_status.get("state") == "degraded":
        logger.warning(
            "Manifest startup build degraded; last-known-good availability=%s",
            manifest_status.get("serving_last_known_good"),
        )
    
    # Start scheduler
    await start_scheduler()
    logger.info("Scheduler started")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    stop_scheduler()
    await close_redis()
    await close_db()
    
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="OneinStack Mirror Generator API - Provides redirect rules for software packages",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(resources_router)
app.include_router(scraper_router)
app.include_router(redirect_router)
app.include_router(manifests_router)


def _public_manifest_health(manifest_status: dict) -> dict:
    """Project authenticated Manifest status onto the public health contract."""
    return {
        "state": manifest_status.get("state", "unknown"),
        "revision": manifest_status.get("revision"),
        "last_success": manifest_status.get("last_success"),
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for Docker healthcheck.
    
    Includes scraper status information.
    """
    from sqlalchemy import desc, select

    from app import redis_client
    from app.database import get_db_session
    from app.models.scrape_log import ScrapeLog
    
    # Get scheduler times from Redis
    scheduler_times = await redis_client.get_scheduler_times()
    
    # Get last successful scrape from database
    last_success = None
    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(ScrapeLog)
                .where(ScrapeLog.status == "success")
                .order_by(desc(ScrapeLog.finished_at))
                .limit(1)
            )
            log = result.scalar_one_or_none()
            if log and log.finished_at:
                last_success = log.finished_at.isoformat()
    except Exception:
        logger.debug("Health check could not query the latest scrape", exc_info=True)
    
    manifest_status = {}
    try:
        manifest_status = await redis_client.get_manifest_status()
    except Exception:
        manifest_status = {
            "state": "degraded",
            "last_error": "manifest status unavailable",
        }

    # Get mirror_type setting
    mirror_type = "redirect"
    try:
        async with get_db_session() as db:
            from app.services import setting_service
            settings_dict = await setting_service.get_all_settings(db)
            mirror_type = settings_dict.get("mirror_type", "redirect")
    except Exception:
        logger.debug("Health check is using the default mirror mode", exc_info=True)
    
    return {
        "status": (
            "degraded"
            if manifest_status.get("state") == "degraded"
            else "healthy"
        ),
        "version": settings.APP_VERSION,
        "mirror_type": mirror_type,
        "last_scrape": scheduler_times.get("last_run"),
        "last_success": last_success,
        "next_scrape": scheduler_times.get("next_run"),
        "manifest": _public_manifest_health(manifest_status),
    }


@app.get("/")
async def root():
    """
    Root endpoint with basic info.
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "OneinStack Mirror Generator API",
        "docs": "/docs" if settings.DEBUG else "Disabled in production",
    }
