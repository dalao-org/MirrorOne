"""
Pure-FTPd scraper.
"""
import re
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


def _version_key(version: str) -> tuple:
    try:
        return tuple(int(x) for x in re.split(r'[._-]', version))
    except ValueError:
        return (0,)


@registry.register("pure_ftpd")
class PureFtpdScraper(BaseScraper):
    """Scraper for Pure-FTPd downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        url = "https://download.pureftpd.org/public/pure-ftpd/releases/"
        
        try:
            response = await self.http_client.get(url, headers=self.get_headers(), timeout=30.0)
            response.raise_for_status()
        except Exception as e:
            result.error_message = f"Failed to fetch Pure-FTPd releases: {e}"
            return result
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if href.endswith(".tar.gz") and href.startswith("pure-ftpd-"):
                version = href.replace("pure-ftpd-", "").replace(".tar.gz", "")
                result.resources.append(Resource(
                    file_name=href,
                    url=url + href,
                    version=version,
                ))

        if result.resources:
            latest = max(result.resources, key=lambda r: _version_key(r.version))
            result.version_metas.append(
                VersionMeta(key="pureftpd_ver", version=latest.version)
            )

        result.success = True
        return result
