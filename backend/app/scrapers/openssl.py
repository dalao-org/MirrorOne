"""
OpenSSL scraper.
"""
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


@registry.register("openssl")
class OpenSSLScraper(BaseScraper):
    """Scraper for OpenSSL downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        releases = await get_github_releases(
            self.http_client,
            "openssl",
            "openssl",
            self.get_headers(),
            include_prerelease=False,
            max_releases=50,
        )
        
        version3_latest = None
        version11_latest = None
        
        for release in releases:
            name = release.get("name", "").lower().replace("openssl ", "")
            assets = release.get("assets", [])
            
            for asset in assets:
                asset_name = asset.get("name", "")
                if asset_name.endswith(".tar.gz"):
                    version = name
                    result.resources.append(Resource(
                        file_name=asset_name,
                        url=asset["browser_download_url"],
                        version=version,
                    ))
                    
                    # Track latest versions
                    if version.startswith("3.") and version3_latest is None:
                        version3_latest = version
                    elif version.startswith("1.1") and version11_latest is None:
                        version11_latest = version
                    break
        
        # Add version metas
        if version3_latest:
            result.version_metas.append(
                VersionMeta(key="openssl3_ver", version=version3_latest)
            )
        if version11_latest:
            result.version_metas.append(
                VersionMeta(key="openssl11_ver", version=version11_latest)
            )
        
        result.success = True
        return result
