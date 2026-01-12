"""
XCache scraper.
"""
from .base import BaseScraper, Resource, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


@registry.register("xcache")
class XCacheScraper(BaseScraper):
    """Scraper for XCache downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        releases = await get_github_releases(
            self.http_client,
            "lighttpd",
            "xcache",
            self.get_headers(),
            include_prerelease=False,
        )
        
        for release in releases:
            tag = release["tag_name"]
            result.resources.append(Resource(
                file_name=f"xcache-{tag}.tar.gz",
                url=f"https://github.com/lighttpd/xcache/archive/refs/tags/{tag}.tar.gz",
                version=tag,
            ))
        
        result.success = True
        return result
