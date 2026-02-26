"""
Boost C++ libraries scraper.
"""
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


@registry.register("boost")
class BoostScraper(BaseScraper):
    """Scraper for Boost C++ libraries downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        max_versions = self.settings.get("boost_max_versions", 5)
        
        # Use GitHub releases instead of JFrog (which redirects)
        releases = await get_github_releases(
            self.http_client,
            "boostorg",
            "boost",
            self.get_headers(),
            include_prerelease=False,
            max_releases=max_versions,
        )
        
        latest_version = None
        for release in releases:
            tag = release["tag_name"]
            version = tag.replace("boost-", "")

            # Look for source tarball in assets
            for asset in release.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".tar.gz") and "source" in name.lower():
                    result.resources.append(Resource(
                        file_name=name,
                        url=asset["browser_download_url"],
                        version=version,
                    ))
                    break
            else:
                # Fallback to tag archive
                file_name = f"boost_{version.replace('.', '_')}.tar.gz"
                result.resources.append(Resource(
                    file_name=file_name,
                    url=f"https://github.com/boostorg/boost/archive/refs/tags/{tag}.tar.gz",
                    version=version,
                ))

            if latest_version is None:
                latest_version = version

        if latest_version:
            result.version_metas.append(
                VersionMeta(key="boost_ver", version=latest_version)
            )

        result.success = True
        return result
