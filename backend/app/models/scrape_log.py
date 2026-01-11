"""
ScrapeLog model for tracking scraper execution history.
"""
from sqlalchemy import String, Text, Float, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from .base import Base


class ScrapeLog(Base):
    """Scrape execution log."""
    
    __tablename__ = "scrape_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scraper_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, failed, partial
    resources_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<ScrapeLog(id={self.id}, scraper={self.scraper_name}, status={self.status})>"
