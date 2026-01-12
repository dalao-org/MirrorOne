"""
Apache APR/APR-util scraper.
"""
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


DEFAULT_BLACKLIST = ["alpha", "beta", "deps", "rc", "win32"]


@registry.register("apr")
class AprScraper(BaseScraper):
    """Scraper for Apache APR and APR-util downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        url = "https://archive.apache.org/dist/apr/"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        max_versions = self.settings.get("apr_max_versions", 3)
        blacklist = self.settings.get("apr_blacklist", DEFAULT_BLACKLIST)
        
        # Get APR versions
        apr_versions = self._extract_versions(soup, "apr-", ["apr-util", "apr-iconv"], blacklist)
        apr_versions = apr_versions[:max_versions]
        
        for version in apr_versions:
            result.resources.append(Resource(
                file_name=f"apr-{version}.tar.gz",
                url=f"https://archive.apache.org/dist/apr/apr-{version}.tar.gz",
                version=version,
            ))
        
        if apr_versions:
            result.version_metas.append(
                VersionMeta(key="apr_ver", version=apr_versions[0])
            )
        
        # Get APR-util versions
        apr_util_versions = self._extract_versions(soup, "apr-util-", [], blacklist)
        apr_util_versions = apr_util_versions[:max_versions]
        
        for version in apr_util_versions:
            result.resources.append(Resource(
                file_name=f"apr-util-{version}.tar.gz",
                url=f"https://archive.apache.org/dist/apr/apr-util-{version}.tar.gz",
                version=version,
            ))
        
        if apr_util_versions:
            result.version_metas.append(
                VersionMeta(key="apr_util_ver", version=apr_util_versions[0])
            )
        
        result.success = True
        return result
    
    def _extract_versions(self, soup, prefix: str, exclude: list[str], blacklist: list[str]) -> list[str]:
        """Extract versions from archive page."""
        versions = []
        
        for link in soup.find_all("a"):
            text = link.text
            if not text.startswith(prefix) or not text.endswith(".tar.gz"):
                continue
            
            # Check exclusions
            if any(ex in text for ex in exclude):
                continue
            
            # Check blacklist
            if any(word in text.lower() for word in blacklist):
                continue
            
            # Extract version
            version = text.replace(".tar.gz", "").replace(prefix, "")
            try:
                [int(c) for c in version.split(".")]
                versions.append(version)
            except ValueError:
                continue
        
        # Sort by version number
        versions.sort(key=lambda x: [int(c) for c in x.split(".")], reverse=True)
        return versions
