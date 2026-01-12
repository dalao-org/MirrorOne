"""
PHP scraper.
"""
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


@registry.register("php")
class PHPScraper(BaseScraper):
    """Scraper for PHP downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        # Get accepted versions from settings
        accepted_versions = self.settings.get("php_accepted_versions", ["8.1", "8.2", "8.3", "8.4", "8.5"])
        
        # Scrape current downloads page
        current_resources = await self._scrape_current_downloads()
        result.resources.extend(current_resources)
        
        # Scrape older releases
        older_resources = await self._scrape_older_releases()
        result.resources.extend(older_resources)
        
        # Generate version metas for accepted versions
        for major_minor in accepted_versions:
            matching = [
                r for r in result.resources
                if r.version.startswith(major_minor + ".")
            ]
            if matching:
                # Get latest version for this major.minor
                latest = sorted(matching, key=lambda r: self._version_key(r.version), reverse=True)[0]
                key = f"php{major_minor.replace('.', '')}_ver"
                result.version_metas.append(VersionMeta(key=key, version=latest.version))
        
        result.success = True
        return result
    
    async def _scrape_current_downloads(self) -> list[Resource]:
        """Scrape current PHP downloads page."""
        resources = []
        
        url = "https://www.php.net/downloads.php"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find all download boxes
        content_boxes = soup.find_all("div", class_="content-box")
        
        for box in content_boxes:
            items = box.find_all("li")
            for item in items:
                if ".tar.gz" not in item.text:
                    continue
                
                link = item.find("a")
                if not link:
                    continue
                
                href = link.get("href", "")
                if href.startswith("/"):
                    href = "https://www.php.net" + href
                
                # Extract version from link text
                link_text = link.text.strip()
                if link_text.startswith("php-") and link_text.endswith(".tar.gz"):
                    version = link_text.replace("php-", "").replace(".tar.gz", "")
                    
                    # Get SHA256 if available
                    sha_span = item.find("span", class_="sha256")
                    sha256 = sha_span.text.strip() if sha_span else None
                    
                    resources.append(Resource(
                        file_name=f"php-{version}.tar.gz",
                        url=href,
                        version=version,
                        checksum=sha256,
                        checksum_type="sha256" if sha256 else None,
                    ))
        
        return resources
    
    async def _scrape_older_releases(self) -> list[Resource]:
        """Scrape older PHP releases."""
        resources = []
        
        url = "https://www.php.net/releases/"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find all release items
        items = soup.find_all("li")
        
        for item in items:
            text = item.text
            if "(tar.gz)" not in text or "Download" in text:
                continue
            
            # Parse format: "PHP X.Y.Z (tar.gz) SHA256"
            parts = text.split()
            if len(parts) >= 4:
                version = parts[1]
                sha256 = parts[3].strip() if len(parts) > 3 else None
                
                link = item.find("a")
                if link:
                    href = link.get("href", "")
                    if href.startswith("/"):
                        href = "https://www.php.net" + href
                    
                    resources.append(Resource(
                        file_name=f"php-{version}.tar.gz",
                        url=href,
                        version=version,
                        checksum=sha256,
                        checksum_type="sha256" if sha256 else None,
                    ))
        
        return resources
    
    def _version_key(self, version: str) -> tuple:
        """Convert version string to sortable tuple."""
        try:
            parts = version.split(".")
            return tuple(int(p) for p in parts[:3])
        except (ValueError, IndexError):
            return (0, 0, 0)
