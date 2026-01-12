"""
Apache HTTPD scraper.
"""
import re
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


DEFAULT_BLACKLIST = ["alpha", "beta", "deps", "rc"]


@registry.register("httpd")
class HttpdScraper(BaseScraper):
    """Scraper for Apache HTTPD downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        blacklist = self.settings.get("httpd_blacklist", DEFAULT_BLACKLIST)
        
        url = "https://archive.apache.org/dist/httpd/"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find all httpd tar.gz files
        versions = []
        for link in soup.find_all("a"):
            href = link.get("href", "")
            text = link.text
            if text.startswith("httpd-") and text.endswith(".tar.gz"):
                # Skip blacklisted versions
                if any(word in text.lower() for word in blacklist):
                    continue
                
                version = text.replace(".tar.gz", "").replace("httpd-", "")
                try:
                    # Validate version format
                    [int(c) for c in version.split(".")]
                    versions.append(version)
                except ValueError:
                    continue
        
        # Sort and get top versions
        versions.sort(key=lambda x: [int(c) for c in x.split(".")], reverse=True)
        max_versions = self.settings.get("httpd_max_versions", 5)
        versions = versions[:max_versions]
        
        for version in versions:
            result.resources.append(Resource(
                file_name=f"httpd-{version}.tar.gz",
                url=f"https://archive.apache.org/dist/httpd/httpd-{version}.tar.gz",
                version=version,
            ))
        
        # Set latest version meta
        if versions:
            result.version_metas.append(
                VersionMeta(key="apache_ver", version=versions[0])
            )
        
        result.success = True
        return result
