"""
htop scraper.
"""
from .base import BaseScraper, Resource, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


@registry.register("htop")
class HtopScraper(BaseScraper):
    """Scraper for htop downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        max_versions = self.settings.get("htop_max_versions", 5)
        
        releases = await get_github_releases(
            self.http_client,
            "htop-dev",
            "htop",
            self.get_headers(),
            include_prerelease=False,
            max_releases=max_versions,
        )
        
        for release in releases:
            version = release["tag_name"]
            
            # Find tar.gz asset
            for asset in release.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".tar.gz"):
                    result.resources.append(Resource(
                        file_name=name,
                        url=asset["browser_download_url"],
                        version=version,
                    ))
                    break
            else:
                # Use source tarball from tag
                result.resources.append(Resource(
                    file_name=f"htop-{version}.tar.gz",
                    url=f"https://github.com/htop-dev/htop/archive/refs/tags/{version}.tar.gz",
                    version=version,
                ))
        
        result.success = True
        return result
