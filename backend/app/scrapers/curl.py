"""
cURL scraper.
"""
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


@registry.register("curl")
class CurlScraper(BaseScraper):
    """Scraper for cURL downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        url = "https://curl.se/download/"
        response = await self.http_client.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table", class_="daily")
        if not table:
            result.error_message = "Could not find downloads table"
            return result
        
        rows = table.find_all("tr", class_=["even", "odd"])
        
        for row in rows:
            tds = row.find_all("td")
            if not tds:
                continue
            
            version = tds[0].text.strip()
            
            # Find tar.gz download link
            for td in tds:
                link = td.find("a")
                if not link:
                    continue
                href = link.get("href", "")
                if ".tar.gz" in href:
                    if not href.startswith("http"):
                        href = "https://curl.se/" + href.lstrip("/")
                    
                    result.resources.append(Resource(
                        file_name=href.split("/")[-1],
                        url=href,
                        version=version,
                    ))
                    break
        
        if result.resources:
            result.version_metas.append(
                VersionMeta(key="curl_ver", version=result.resources[0].version)
            )
        
        result.success = True
        return result
