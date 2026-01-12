"""
PostgreSQL scraper.
"""
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


@registry.register("postgresql")
class PostgreSQLScraper(BaseScraper):
    """Scraper for PostgreSQL downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        url = "https://ftp.postgresql.org/pub/source/"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        pre = soup.find("pre")
        if not pre:
            result.error_message = "Could not find version list"
            return result
        
        versions = []
        for link in pre.find_all("a"):
            text = link.text.strip()
            # Skip parent dir and pre-release versions
            if any(s in text.lower() for s in ["..", "beta", "rc", "alpha"]):
                continue
            
            # Extract version number
            version_str = text.replace("/", "").replace("v", "")
            try:
                float(version_str)  # Validate it's a valid float
                versions.append(version_str)
            except ValueError:
                continue
        
        # Sort and limit
        versions.sort(key=float, reverse=True)
        max_versions = self.settings.get("postgresql_max_versions", 10)
        versions = versions[:max_versions]
        
        for version in versions:
            result.resources.append(Resource(
                file_name=f"postgresql-{version}.tar.gz",
                url=f"https://ftp.postgresql.org/pub/source/v{version}/postgresql-{version}.tar.gz",
                version=version,
            ))
        
        if result.resources:
            result.version_metas.append(
                VersionMeta(key="pgsql_ver", version=result.resources[0].version)
            )
        
        result.success = True
        return result
