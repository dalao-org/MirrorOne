"""
phpMyAdmin scraper.
"""
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


@registry.register("phpmyadmin")
class PhpMyAdminScraper(BaseScraper):
    """Scraper for phpMyAdmin downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        url = "https://www.phpmyadmin.net/downloads/"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        tables = soup.find_all("table", class_="table-condensed")
        
        versions_found = []
        
        for table in tables:
            tbody = table.find("tbody")
            if not tbody:
                continue
            
            rows = tbody.find_all("tr")
            for row in rows:
                text = row.text.lower()
                
                # Skip non-relevant entries
                if ".tar.gz" not in text or "all-languages" not in text:
                    continue
                if "snapshot" in text or "latest" in text:
                    continue
                
                # Find download link
                link = row.find("a")
                if not link:
                    continue
                
                href = link.get("href", "")
                sha256 = link.get("data-sha256", "")
                link_text = link.text.strip()
                
                # Extract version
                version = link_text.replace("phpMyAdmin-", "").replace("-all-languages.tar.gz", "")
                
                result.resources.append(Resource(
                    file_name=href.split("/")[-1],
                    url=href,
                    version=version,
                    checksum=sha256,
                    checksum_type="sha256" if sha256 else None,
                ))
                versions_found.append(version)
        
        # Add version metas
        if len(versions_found) >= 1:
            result.version_metas.append(
                VersionMeta(key="phpmyadmin_ver", version=versions_found[0])
            )
        if len(versions_found) >= 2:
            result.version_metas.append(
                VersionMeta(key="phpmyadmin_oldver", version=versions_found[1])
            )
        
        result.success = True
        return result
