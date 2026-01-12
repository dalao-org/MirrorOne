"""
Tengine scraper.
"""
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


@registry.register("tengine")
class TengineScraper(BaseScraper):
    """Scraper for Tengine (Alibaba's Nginx fork) downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        releases = await get_github_releases(
            self.http_client,
            "alibaba",
            "tengine",
            self.get_headers(),
            include_prerelease=False,
            max_releases=10,
        )
        
        for release in releases:
            tag = release["tag_name"]
            version = tag.lstrip("v")
            result.resources.append(Resource(
                file_name=f"tengine-{tag}.tar.gz",
                url=f"https://github.com/alibaba/tengine/archive/refs/tags/{tag}.tar.gz",
                version=version,
            ))
        
        if result.resources:
            result.version_metas.append(
                VersionMeta(key="tengine_ver", version=result.resources[0].version)
            )
        
        result.success = True
        return result
