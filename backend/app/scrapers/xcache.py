"""
XCache scraper.
"""
from .base import BaseScraper, Resource, ScrapeResult
from .registry import registry
from .github_utils import get_github_tags, filter_blacklist


@registry.register("xcache")
class XCacheScraper(BaseScraper):
    """Scraper for XCache downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        # XCache repo has no formal releases, only tags
        tags = await get_github_tags(
            self.http_client,
            "lighttpd",
            "xcache",
            self.get_headers(),
            max_tags=10,
        )
        
        # Filter out rc/beta/alpha versions
        tags = filter_blacklist(tags)
        
        for tag in tags:
            result.resources.append(Resource(
                file_name=f"xcache-{tag}.tar.gz",
                url=f"https://github.com/lighttpd/xcache/archive/refs/tags/{tag}.tar.gz",
                version=tag,
            ))
        
        result.success = True
        return result
