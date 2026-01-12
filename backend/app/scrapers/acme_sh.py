"""
acme.sh scraper.
"""
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


@registry.register("acme_sh")
class AcmeShScraper(BaseScraper):
    """Scraper for acme.sh downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        releases = await get_github_releases(
            self.http_client,
            "acmesh-official",
            "acme.sh",
            self.get_headers(),
            include_prerelease=False,
            max_releases=1,
        )
        
        if releases:
            release = releases[0]
            version = release["tag_name"]
            
            result.resources.append(Resource(
                file_name="acme.sh-master.tar.gz",
                url=f"https://github.com/acmesh-official/acme.sh/archive/refs/tags/{version}.tar.gz",
                version=version,
            ))
            
            result.version_metas.append(
                VersionMeta(key="acme_sh_ver", version=version)
            )
        
        result.success = True
        return result
