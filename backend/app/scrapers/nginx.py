"""
Nginx scraper.
"""
import re
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


@registry.register("nginx")
class NginxScraper(BaseScraper):
    """Scraper for Nginx downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        url = "https://nginx.org/en/download.html"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Get mainline version
        mainline_section = soup.find("h4", string="Mainline version")
        if mainline_section:
            table = mainline_section.find_next("table")
            version_info = self._parse_version_table(table)
            if version_info:
                result.resources.append(version_info)
                result.version_metas.append(
                    VersionMeta(key="nginx_ver", version=version_info.version)
                )
        
        # Get stable version
        stable_section = soup.find("h4", string="Stable version")
        if stable_section:
            table = stable_section.find_next("table")
            version_info = self._parse_version_table(table)
            if version_info:
                result.resources.append(version_info)
        
        # Get legacy versions
        legacy_count = self.settings.get("nginx_legacy_versions_count", 5)
        legacy_section = soup.find("h4", string="Legacy versions")
        if legacy_section:
            tables = legacy_section.find_next_siblings("table")[:legacy_count]
            for table in tables:
                version_info = self._parse_version_table(table)
                if version_info:
                    result.resources.append(version_info)
        
        result.success = True
        return result
    
    def _parse_version_table(self, table) -> Resource | None:
        """Parse a version table to extract download info."""
        if not table:
            return None
        
        # Find the tar.gz download link
        link = table.find("a", href=re.compile(r"nginx-[\d.]+\.tar\.gz$"))
        if not link:
            return None
        
        href = link.get("href", "")
        if href.startswith("/"):
            href = "https://nginx.org" + href
        
        # Extract version from filename
        match = re.search(r"nginx-([\d.]+)\.tar\.gz", href)
        if not match:
            return None
        
        version = match.group(1)
        
        return Resource(
            file_name=f"nginx-{version}.tar.gz",
            url=href,
            version=version,
        )
