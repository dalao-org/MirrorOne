"""
Python scraper.
"""
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


# Default values for settings (used as fallbacks)
DEFAULT_ACCEPTED_VERSIONS = ["2.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]


@registry.register("python")
class PythonScraper(BaseScraper):
    """Scraper for Python downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        url = "https://www.python.org/ftp/python/"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        pre = soup.find("pre")
        if not pre:
            result.error_message = "Could not find version list"
            return result
        
        # Get accepted versions from settings
        accepted_versions = self.settings.get("python_accepted_versions", DEFAULT_ACCEPTED_VERSIONS)
        
        # Collect all versions
        all_versions = []
        for link in pre.find_all("a"):
            version = link.text.strip().rstrip("/")
            if any(version.startswith(allowed) for allowed in accepted_versions):
                all_versions.append(version)
        
        # Get latest 3 revisions per minor version
        for minor in accepted_versions:
            minor_versions = [v for v in all_versions if v.startswith(minor)]
            
            # Filter valid versions with revision number
            valid_versions = []
            for v in minor_versions:
                parts = v.split(".")
                if len(parts) >= 3:
                    try:
                        int(parts[2])
                        valid_versions.append(v)
                    except ValueError:
                        continue
            
            # Sort by revision and take top 3
            valid_versions.sort(
                key=lambda x: int(x.split(".")[2]),
                reverse=True
            )
            
            for version in valid_versions[:3]:
                result.resources.append(Resource(
                    file_name=f"Python-{version}.tgz",
                    url=f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz",
                    version=version,
                ))
            
            # Generate version meta for this minor version (e.g., python313_ver)
            if valid_versions:
                key = f"python{minor.replace('.', '')}_ver"
                result.version_metas.append(VersionMeta(key=key, version=valid_versions[0]))
        
        result.success = True
        return result

