"""
nghttp2 scraper.
"""
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


@registry.register("nghttp2")
class Nghttp2Scraper(BaseScraper):
    """Scraper for nghttp2 downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        releases = await get_github_releases(
            self.http_client,
            "nghttp2",
            "nghttp2",
            self.get_headers(),
            include_prerelease=False,
            max_releases=10,
        )
        
        for release in releases:
            tag = release["tag_name"]
            version = tag.lstrip("v")
            
            for asset in release.get("assets", []):
                name = asset.get("name", "")
                if "tar.gz" in name:
                    result.resources.append(Resource(
                        file_name=name,
                        url=asset["browser_download_url"],
                        version=version,
                    ))
                    break
        
        if result.resources:
            result.version_metas.append(
                VersionMeta(key="nghttp2_ver", version=result.resources[0].version)
            )
        
        result.success = True
        return result
