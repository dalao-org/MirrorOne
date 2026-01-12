"""
pip/setuptools scraper.
"""
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, ScrapeResult
from .registry import registry

BLACK_LIST_WORDS = ["test", "b1", "b2", "b3", "a1", "a2", "rc"]


@registry.register("pip")
class PipScraper(BaseScraper):
    """Scraper for pip downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        max_versions = self.settings.get("pip_max_versions", 5)
        
        # Scrape pip from PyPI
        await self._scrape_pypi_package("pip", max_versions, result)
        
        # Scrape setuptools from PyPI
        await self._scrape_pypi_package("setuptools", max_versions, result)
        
        result.success = True
        return result
    
    async def _scrape_pypi_package(
        self, package: str, max_versions: int, result: ScrapeResult
    ) -> None:
        """Scrape a package from PyPI."""
        try:
            url = f"https://pypi.org/simple/{package}/"
            response = await self.http_client.get(url, headers=self.get_headers())
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find all tar.gz links
            versions = []
            for link in soup.find_all("a"):
                href = link.get("href", "")
                text = link.text
                
                if text.endswith(".tar.gz") and package in text.lower():
                    # Filter blacklisted versions
                    if any(word in text.lower() for word in BLACK_LIST_WORDS):
                        continue
                    
                    # Extract version
                    version = text.replace(f"{package}-", "").replace(".tar.gz", "")
                    versions.append((version, href, text))
            
            # Sort and get top versions
            versions.reverse()  # PyPI lists oldest first
            versions = versions[:max_versions]
            
            for version, href, filename in versions:
                result.resources.append(Resource(
                    file_name=filename,
                    url=href.split("#")[0],  # Remove hash fragment
                    version=version,
                ))
        except Exception:
            pass
