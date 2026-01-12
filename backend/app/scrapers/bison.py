"""
GNU Bison scraper.
"""
import re
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, ScrapeResult
from .registry import registry


@registry.register("bison")
class BisonScraper(BaseScraper):
    """Scraper for GNU Bison downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        url = "https://ftp.gnu.org/gnu/bison/"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        pattern = re.compile(r"bison-\d+\.\d+(\.\d+)?\.tar\.gz$")
        
        for link in soup.find_all("a", href=pattern):
            href = link.get("href", "")
            version = href.replace("bison-", "").replace(".tar.gz", "")
            result.resources.append(Resource(
                file_name=href,
                url=url + href,
                version=version,
            ))
        
        result.success = True
        return result
