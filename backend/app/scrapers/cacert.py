"""
CA certificates scraper.
"""
from .base import BaseScraper, Resource, ScrapeResult
from .registry import registry


@registry.register("cacert")
class CacertScraper(BaseScraper):
    """Scraper for Mozilla CA certificate bundle."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        # This is a static URL that always points to the latest bundle
        result.resources.append(Resource(
            file_name="cacert.pem",
            url="https://curl.se/ca/cacert.pem",
            version="latest",
        ))
        
        result.success = True
        return result
