"""
Base scraper class and data structures.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import ClassVar, Any
import httpx


@dataclass
class Resource:
    """Scraped resource data."""
    file_name: str
    url: str
    version: str
    checksum: str | None = None
    checksum_type: str | None = None


@dataclass
class VersionMeta:
    """Version metadata for suggest_versions.txt."""
    key: str
    version: str


@dataclass
class ScrapeResult:
    """Result of a scrape operation."""
    scraper_name: str
    success: bool = False
    resources: list[Resource] = field(default_factory=list)
    version_metas: list[VersionMeta] = field(default_factory=list)
    error_message: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    
    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0.0
    
    @property
    def resources_count(self) -> int:
        """Get count of resources."""
        return len(self.resources)
    
    @property
    def status(self) -> str:
        """Get status string."""
        if self.success:
            return "success"
        elif self.resources:
            return "partial"
        else:
            return "failed"

class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    
    Subclasses must implement the `scrape` method and set the `name` class variable.
    """
    
    name: ClassVar[str] = "base"
    
    def __init__(self, settings: dict[str, Any], http_client: httpx.AsyncClient):
        """
        Initialize scraper.
        
        Args:
            settings: Dictionary of settings from database
            http_client: Shared httpx async client
        """
        self.settings = settings
        self.http_client = http_client
        self.github_token = settings.get("github_api_token")
    
    @abstractmethod
    async def scrape(self) -> ScrapeResult:
        """
        Execute scrape logic.
        
        Returns:
            ScrapeResult with scraped resources and metadata
        """
        pass
    
    def get_headers(self) -> dict[str, str]:
        """Get HTTP request headers with optional GitHub auth."""
        headers = {
            "User-Agent": "OneinStack-Mirror-Bot/2.0",
            "Accept": "application/json, text/html, */*",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers
    
    async def log(self, message: str, level: str = "info") -> None:
        """Broadcast a log message for this scraper."""
        from app.core.log_broadcaster import broadcaster, LogLevel
        
        level_map = {
            "info": LogLevel.INFO,
            "success": LogLevel.SUCCESS,
            "warning": LogLevel.WARNING,
            "error": LogLevel.ERROR,
        }
        await broadcaster.broadcast(
            message=message,
            level=level_map.get(level, LogLevel.INFO),
            scraper=self.name,
        )
    
    async def fetch(self, url: str, method: str = "GET", **kwargs) -> httpx.Response:
        """
        Fetch a URL with logging.
        
        Broadcasts request start, completion or error.
        """
        # Extract just the path for cleaner logs
        from urllib.parse import urlparse
        parsed = urlparse(url)
        short_url = parsed.netloc + parsed.path[:50] + ("..." if len(parsed.path) > 50 else "")
        
        await self.log(f"📡 {method} {short_url}")
        
        try:
            if method.upper() == "GET":
                response = await self.http_client.get(url, headers=self.get_headers(), **kwargs)
            else:
                response = await self.http_client.request(method, url, headers=self.get_headers(), **kwargs)
            
            status = response.status_code
            size = len(response.content) if response.content else 0
            size_str = f"{size // 1024}KB" if size > 1024 else f"{size}B"
            
            if status >= 400:
                await self.log(f"❌ {status} {short_url}", "error")
            else:
                await self.log(f"✓ {status} {short_url} ({size_str})", "success")
            
            return response
            
        except Exception as e:
            await self.log(f"❌ Error: {short_url} - {type(e).__name__}", "error")
            raise
    
    async def safe_scrape(self) -> ScrapeResult:
        """
        Execute scrape with exception handling.
        
        Returns:
            ScrapeResult, with error_message set if an exception occurred
        """
        from app.core.log_broadcaster import broadcaster, LogLevel
        
        result = ScrapeResult(scraper_name=self.name)
        
        await broadcaster.broadcast(
            f"🔍 Starting scraper: {self.name}",
            level=LogLevel.INFO,
            scraper=self.name,
        )
        
        try:
            result = await self.scrape()
            result.success = True
            
            await broadcaster.broadcast(
                f"✅ {self.name}: Found {result.resources_count} resources",
                level=LogLevel.SUCCESS,
                scraper=self.name,
            )
        except Exception as e:
            result.error_message = f"{type(e).__name__}: {str(e)}"
            result.success = False
            
            await broadcaster.broadcast(
                f"❌ {self.name} failed: {result.error_message}",
                level=LogLevel.ERROR,
                scraper=self.name,
            )
        finally:
            result.finished_at = datetime.now(UTC)
        return result

