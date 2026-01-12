"""
PHP patches scraper.
Static patches required for PHP builds.
"""
from .base import BaseScraper, Resource, ScrapeResult
from .registry import registry


# Static patch URLs
PHP_PATCHES = [
    {
        "file_name": "fpm-race-condition.patch",
        "url": "https://bugs.php.net/patch-display.php?bug_id=65398&patch=fpm-race-condition.patch&revision=1375772074&download=1",
        "version": "fixed",
    },
]


@registry.register("php_patches")
class PhpPatchesScraper(BaseScraper):
    """Scraper for PHP build patches."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        for patch in PHP_PATCHES:
            result.resources.append(Resource(
                file_name=patch["file_name"],
                url=patch["url"],
                version=patch["version"],
            ))
        
        result.success = True
        return result
