"""
Phalcon (cphalcon) PHP framework scraper.
"""
from .base import BaseScraper, Resource, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


@registry.register("cphalcon")
class CphalconScraper(BaseScraper):
    """Scraper for Phalcon PHP framework downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        releases = await get_github_releases(
            self.http_client,
            "phalcon",
            "cphalcon",
            self.get_headers(),
            include_prerelease=False,
        )
        
        for release in releases:
            tag = release["tag_name"]
            version = tag.lstrip("v")
            result.resources.append(Resource(
                file_name=f"cphalcon-{tag}.tar.gz",
                url=f"https://github.com/phalcon/cphalcon/archive/refs/tags/{tag}.tar.gz",
                version=version,
            ))
        
        result.success = True
        return result
