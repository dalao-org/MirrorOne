"""
Fail2ban scraper.
"""
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


@registry.register("fail2ban")
class Fail2banScraper(BaseScraper):
    """Scraper for Fail2ban downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        releases = await get_github_releases(
            self.http_client,
            "fail2ban",
            "fail2ban",
            self.get_headers(),
            include_prerelease=False,
            max_releases=1,
        )
        
        if releases:
            release = releases[0]
            version = release["tag_name"]
            
            result.resources.append(Resource(
                file_name=f"fail2ban-{version}.tar.gz",
                url=f"https://github.com/fail2ban/fail2ban/archive/refs/tags/{version}.tar.gz",
                version=version,
            ))
            
            result.version_metas.append(
                VersionMeta(key="fail2ban_ver", version=version)
            )
        
        result.success = True
        return result
