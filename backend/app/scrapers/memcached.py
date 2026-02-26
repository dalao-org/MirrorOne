"""
Memcached scraper.
"""
import re
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry
from .github_utils import get_github_tags


@registry.register("memcached")
class MemcachedScraper(BaseScraper):
    """Scraper for Memcached downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        max_versions = self.settings.get("memcached_max_versions", 5)
        
        all_tags = await get_github_tags(
            self.http_client,
            "memcached",
            "memcached",
            self.get_headers(),
            max_tags=None,
        )

        # The memcached repo contains non-version tags (e.g. 'flash-with-wbuf-stack').
        # Keep only tags that look like version numbers: optional 'v' then digits and dots.
        _version_re = re.compile(r'^v?\d+\.\d+')
        tags = [t for t in all_tags if _version_re.match(t)][:max_versions]

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
