"""
Scrape log schemas.
"""
from pydantic import BaseModel
from datetime import datetime


class ScrapeLogResponse(BaseModel):
    """Scrape log response schema."""
    id: int
    scraper_name: str
    status: str
    resources_count: int
    error_message: str | None
    duration_seconds: float
    started_at: datetime
    finished_at: datetime | None
    
    model_config = {"from_attributes": True}


class ScrapeLogListResponse(BaseModel):
    """Scrape log list response."""
    total: int
    logs: list[ScrapeLogResponse]


class ScraperStatusResponse(BaseModel):
    """Scheduler status response."""
    enabled: bool
    interval_hours: int
    last_run: str | None
    next_run: str | None
    available_scrapers: list[str]
