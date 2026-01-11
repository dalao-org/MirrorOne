"""
Redis scraper.
"""
import re
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


@registry.register("redis")
class RedisScraper(BaseScraper):
    """Scraper for Redis downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        url = "https://download.redis.io/releases/"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find all redis tar.gz files
        links = soup.find_all("a", href=re.compile(r"redis-[\d.]+\.tar\.gz$"))
        
        versions = []
        for link in links:
            href = link.get("href", "")
            match = re.search(r"redis-([\d.]+)\.tar\.gz", href)
            if match:
                version = match.group(1)
                full_url = f"https://download.redis.io/releases/{href}"
                versions.append((version, full_url))
        
        # Sort by version (newest first) and take recent ones
        versions.sort(key=lambda x: self._version_key(x[0]), reverse=True)
        
        for version, url in versions[:10]:  # Keep last 10 versions
            result.resources.append(Resource(
                file_name=f"redis-{version}.tar.gz",
                url=url,
                version=version,
            ))
        
        if result.resources:
            result.version_metas.append(
                VersionMeta(key="redis_ver", version=result.resources[0].version)
            )
        
        result.success = True
        return result
    
    def _version_key(self, version: str) -> tuple:
        """Convert version string to sortable tuple."""
        try:
            parts = version.split(".")
            return tuple(int(p) for p in parts)
        except (ValueError, IndexError):
            return (0,)
