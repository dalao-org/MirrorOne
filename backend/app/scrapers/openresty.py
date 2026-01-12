"""
OpenResty scraper.
"""
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


@registry.register("openresty")
class OpenRestyScraper(BaseScraper):
    """Scraper for OpenResty downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        max_releases = self.settings.get("openresty_max_releases", 3)
        
        releases = await get_github_releases(
            self.http_client,
            "openresty",
            "openresty",
            self.get_headers(),
            include_prerelease=False,
            max_releases=max_releases,
        )
        
        for release in releases:
            version = release["tag_name"].lstrip("v")
            result.resources.append(Resource(
                file_name=f"openresty-{version}.tar.gz",
                url=f"https://openresty.org/download/openresty-{version}.tar.gz",
                version=version,
            ))
        
        if result.resources:
            result.version_metas.append(
                VersionMeta(key="openresty_ver", version=result.resources[0].version)
            )
        
        result.success = True
        return result
