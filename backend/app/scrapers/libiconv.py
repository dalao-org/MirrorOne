"""
libiconv scraper.
"""
import re
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


@registry.register("libiconv")
class LibiconvScraper(BaseScraper):
    """Scraper for libiconv downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        url = "https://ftp.gnu.org/gnu/libiconv/"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        pattern = re.compile(r"libiconv-\d+\.\d+(\.\d+)?\.tar\.gz$")
        
        for link in soup.find_all("a", href=pattern):
            href = link.get("href", "")
            version = href.replace("libiconv-", "").replace(".tar.gz", "")
            result.resources.append(Resource(
                file_name=href,
                url=url + href,
                version=version,
            ))
        
        if result.resources:
            result.version_metas.append(
                VersionMeta(key="libiconv_ver", version=result.resources[0].version)
            )
        
        result.success = True
        return result
