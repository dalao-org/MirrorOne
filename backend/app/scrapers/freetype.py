"""
FreeType scraper.
"""
import re
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


@registry.register("freetype")
class FreetypeScraper(BaseScraper):
    """Scraper for FreeType downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        url = "https://download.savannah.gnu.org/releases/freetype/"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        pattern = re.compile(r"(freetype-)(?P<v>\d+\.\d+\.\d+)(\.tar\.gz)")
        
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            match = pattern.search(href)
            if match:
                version = match.group("v")
                result.resources.append(Resource(
                    file_name=href,
                    url=url + href,
                    version=version,
                ))
        
        if result.resources:
            result.version_metas.append(
                VersionMeta(key="freetype_ver", version=result.resources[0].version)
            )
        
        result.success = True
        return result
