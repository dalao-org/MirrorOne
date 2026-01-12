"""
Memcached scraper.
"""
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry
from .github_utils import get_github_tags


@registry.register("memcached")
class MemcachedScraper(BaseScraper):
    """Scraper for Memcached downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        max_versions = self.settings.get("memcached_max_versions", 5)
        
        tags = await get_github_tags(
            self.http_client,
            "memcached",
            "memcached",
            self.get_headers(),
            max_tags=max_versions,
        )
        
        for tag in tags:
            version = tag.lstrip("v")
            result.resources.append(Resource(
                file_name=f"memcached-{version}.tar.gz",
                url=f"http://www.memcached.org/files/memcached-{version}.tar.gz",
                version=version,
            ))
        
        if result.resources:
            result.version_metas.append(
                VersionMeta(key="memcached_ver", version=result.resources[0].version)
            )
        
        result.success = True
        return result
