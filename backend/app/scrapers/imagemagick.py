"""
ImageMagick scraper.
"""
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


@registry.register("imagemagick")
class ImageMagickScraper(BaseScraper):
    """Scraper for ImageMagick downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        url = "https://imagemagick.org/archive/"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if href.startswith("ImageMagick-") and href.endswith(".tar.gz"):
                version = href.replace("ImageMagick-", "").replace(".tar.gz", "")
                result.resources.append(Resource(
                    file_name=href,
                    url=url + href,
                    version=version,
                ))
        
        if result.resources:
            result.version_metas.append(
                VersionMeta(key="imagemagick_ver", version=result.resources[0].version)
            )
        
        result.success = True
        return result
