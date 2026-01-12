"""
MariaDB scraper.
"""
import logging

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry

logger = logging.getLogger(__name__)

VERSIONS_API = "https://downloads.mariadb.org/rest-api/mariadb/"
VERSION_RESOURCE_API = "https://downloads.mariadb.org/rest-api/mariadb/{version}/"
ONEINSTACK_COMPATIBLE_VERSIONS = ["5.5", "10.4", "10.5", "10.11", "11.4"]


@registry.register("mariadb")
class MariaDBScraper(BaseScraper):
    """Scraper for MariaDB downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        max_per_branch = self.settings.get("mariadb_max_per_branch", 3)
        
        try:
            # Get available major versions
            response = await self.http_client.get(VERSIONS_API, headers=self.get_headers())
            response.raise_for_status()
            data = response.json()
            
            # Get stable LTS versions
            live_branches = [
                b["release_id"] for b in data.get("major_releases", [])
                if b.get("release_status") == "Stable"
                and b.get("release_support_type") == "Long Term Support"
            ]
            
            # Combine with OneinStack compatible versions
            all_branches = list(set(ONEINSTACK_COMPATIBLE_VERSIONS + live_branches))
            all_branches.sort(reverse=True)
            
            for branch in all_branches:
                await self._fetch_branch_packages(
                    branch, max_per_branch, result
                )
            
            result.success = True
        except Exception as e:
            result.error_message = str(e)
        
        return result
    
    async def _fetch_branch_packages(
        self, branch: str, max_packages: int, result: ScrapeResult
    ) -> None:
        """Fetch packages for a specific MariaDB version branch."""
        try:
            url = VERSION_RESOURCE_API.format(version=branch)
            response = await self.http_client.get(url, headers=self.get_headers())
            response.raise_for_status()
            data = response.json()
            
            releases = data.get("releases", {})
            count = 0
            latest_version = None
            
            for release_id, release_data in releases.items():
                if count >= max_packages:
                    break
                
                files = release_data.get("files", [])
                
                # Find Linux x86_64 systemd package
                linux_pkg = None
                for f in files:
                    if (f.get("os") == "Linux" and 
                        f.get("cpu", "").lower() == "x86_64" and
                        "linux-systemd" in f.get("file_name", "")):
                        linux_pkg = f
                        break
                
                if not linux_pkg:
                    continue
                
                checksum = linux_pkg.get("checksum", {})
                result.resources.append(Resource(
                    file_name=linux_pkg["file_name"],
                    url=linux_pkg["file_download_url"],
                    version=release_data.get("release_id", release_id),
                    checksum=checksum.get("md5sum"),
                    checksum_type="md5" if checksum.get("md5sum") else None,
                ))
                
                if latest_version is None:
                    latest_version = release_data.get("release_id", release_id)
                
                count += 1
            
            # Add version meta for this branch
            if latest_version:
                meta_key = f"mariadb{branch.replace('.', '')}_ver"
                result.version_metas.append(
                    VersionMeta(key=meta_key, version=latest_version)
                )
        except Exception as e:
            logger.warning(f"Failed to fetch MariaDB branch {branch}: {e}")
