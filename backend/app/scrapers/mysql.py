"""
MySQL scraper.
"""
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


BLACK_LIST_KEYWORD = ["arm", "32-bit", "test", "minimal", "ia-64", "debug"]
ACCEPTED_VERSIONS = ["5.5", "5.6", "5.7", "8.0", "8.4", "9.0", "9.1"]


@registry.register("mysql")
class MySQLScraper(BaseScraper):
    """Scraper for MySQL downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        # Get older versions from archives
        archive_releases = await self._get_archive_versions()
        result.resources.extend(archive_releases)
        
        # Get latest versions
        latest_releases = await self._get_latest_versions()
        result.resources.extend(latest_releases)
        
        # Create version metas
        all_releases = archive_releases + latest_releases
        sorted_releases = sorted(
            all_releases,
            key=lambda x: [int(c) for c in x.version.split(".")],
            reverse=True
        )
        
        # Group by major.minor version
        version_groups = {}
        for r in sorted_releases:
            major_minor = ".".join(r.version.split(".")[:2])
            if major_minor not in version_groups:
                version_groups[major_minor] = r.version
        
        # Add version metas
        version_mapping = {
            "8.4": "mysql84_ver",
            "8.0": "mysql80_ver",
            "5.7": "mysql57_ver",
            "5.6": "mysql56_ver",
            "5.5": "mysql55_ver",
        }
        for mm, meta_key in version_mapping.items():
            if mm in version_groups:
                result.version_metas.append(
                    VersionMeta(key=meta_key, version=version_groups[mm])
                )
        
        result.success = True
        return result
    
    async def _parse_mysql_table(self, url: str) -> Resource | None:
        """Parse MySQL download table to extract package info."""
        try:
            response = await self.http_client.get(url, headers=self.get_headers())
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            table = soup.find("table")
            if not table:
                return None
            
            rows = table.find_all("tr")
            rows = [row for row in rows if len(row.find_all("td")) == 4]
            
            for row in rows:
                td_elements = row.find_all("td")
                package_name = td_elements[0].text
                
                if any(kw in package_name.lower() for kw in BLACK_LIST_KEYWORD):
                    continue
                
                link = td_elements[3].find("a")
                if not link:
                    continue
                download_url = link.get("href", "")
                
                next_row = row.find_next_sibling("tr")
                if not next_row:
                    continue
                next_tds = next_row.find_all("td")
                if not next_tds:
                    continue
                
                file_name = next_tds[0].text.replace("(", "").replace(")", "").strip()
                if ".tar.gz" not in file_name:
                    continue
                
                md5_elem = next_tds[1].find("code", class_="md5") if len(next_tds) > 1 else None
                md5 = md5_elem.text if md5_elem else None
                
                if download_url.startswith("/"):
                    download_url = "https://downloads.mysql.com" + download_url
                
                return Resource(
                    file_name=file_name,
                    url=download_url,
                    version="",  # Will be set by caller
                    checksum=md5,
                    checksum_type="md5" if md5 else None,
                )
        except Exception:
            pass
        return None
    
    async def _get_archive_versions(self) -> list[Resource]:
        """Get older MySQL versions from archives."""
        resources = []
        
        try:
            url = "https://downloads.mysql.com/archives/community/"
            response = await self.http_client.get(url, headers=self.get_headers())
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            label = soup.find("label", string="Product Version:")
            if not label or not label.parent:
                return resources
            
            options = label.parent.find_all("option")
            versions = [
                opt.text for opt in options
                if any(opt.text.startswith(av) for av in ACCEPTED_VERSIONS)
                and not any(c.isalpha() for c in opt.text)
            ]
            
            for version in versions[:10]:  # Limit to 10 archive versions
                pkg_url = f"https://downloads.mysql.com/archives/community/?tpl=platform&os=2&version={version}"
                resource = await self._parse_mysql_table(pkg_url)
                if resource:
                    resource.version = version
                    resources.append(resource)
        except Exception:
            pass
        
        return resources
    
    async def _get_latest_versions(self) -> list[Resource]:
        """Get latest MySQL versions."""
        resources = []
        
        try:
            url = "https://dev.mysql.com/downloads/mysql/"
            response = await self.http_client.get(url, headers=self.get_headers())
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            select = soup.find("select", id="version")
            if not select:
                return resources
            
            options = select.find_all("option")
            versions = [
                opt.text.strip() for opt in options
                if not any(c.isalpha() for c in opt.text)
            ]
            
            for version in versions:
                pkg_url = f"https://dev.mysql.com/downloads/mysql/?tpl=platform&os=2&version={version}&osva="
                resource = await self._parse_mysql_table(pkg_url)
                if resource:
                    resource.version = version
                    resources.append(resource)
        except Exception:
            pass
        
        return resources
