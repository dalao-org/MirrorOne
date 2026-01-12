"""
MySQL scraper.
"""
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


# Default values for settings (used as fallbacks)
DEFAULT_BLACKLIST = ["arm", "32-bit", "test", "minimal", "ia-64", "debug"]
DEFAULT_ACCEPTED_VERSIONS = ["5.5", "5.6", "5.7", "8.0", "8.4", "9.0", "9.1", "9.2", "9.3", "9.4", "9.5"]


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
        
        # Add version metas dynamically based on accepted_versions
        accepted_versions = self.settings.get("mysql_accepted_versions", DEFAULT_ACCEPTED_VERSIONS)
        for major_minor in accepted_versions:
            if major_minor in version_groups:
                # Generate key like "mysql84_ver" from "8.4"
                key = f"mysql{major_minor.replace('.', '')}_ver"
                result.version_metas.append(
                    VersionMeta(key=key, version=version_groups[major_minor])
                )
        
        result.success = True
        return result
    
    async def _parse_mysql_table(self, url: str) -> Resource | None:
        """Parse MySQL download table to extract package info.
        
        MySQL website structure:
        - Each download entry spans TWO rows:
          - Row 1: Package description, date, size, Download button
          - Row 2: Filename (in parentheses) and MD5 hash
        - Modern versions use .tar.xz, older versions use .tar.gz
        """
        import re
        
        try:
            response = await self.http_client.get(url, headers=self.get_headers())
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find all download links by href pattern (more reliable than text matching)
            download_links = soup.find_all("a", href=re.compile(r"/get/.*|/archives/get/.*"))
            if not download_links:
                return None
            
            blacklist = self.settings.get("mysql_blacklist", DEFAULT_BLACKLIST)
            
            for link in download_links:
                download_url = link.get("href", "")
                
                # Extract filename directly from URL (most reliable method)
                # URL format: /archives/get/p/23/file/mysql-8.0.40-linux-glibc2.28-x86_64.tar.xz
                url_parts = download_url.split("/")
                if not url_parts:
                    continue
                
                file_name = url_parts[-1]
                
                # Must be a tar archive
                if not re.search(r'\.tar(?:\.gz|\.xz)?$', file_name):
                    continue
                
                # Apply blacklist filter on filename
                if any(kw in file_name.lower() for kw in blacklist):
                    continue
                
                # Prefer 64-bit x86 packages
                if "x86_64" not in file_name and "x86-64" not in file_name:
                    # Check the row text for 64-bit indication
                    row = link.find_parent("tr")
                    if row:
                        row_text = row.get_text().lower()
                        # Match various formats: "64-bit", "64bit", "x86, 64-bit"
                        if "64-bit" not in row_text and "64bit" not in row_text:
                            continue
                
                # Build full download URL
                if download_url.startswith("/"):
                    if "dev.mysql.com" in url:
                        download_url = "https://dev.mysql.com" + download_url
                    else:
                        download_url = "https://downloads.mysql.com" + download_url
                
                # Try to extract MD5 from the next row (sibling)
                md5 = None
                row = link.find_parent("tr")
                if row:
                    next_row = row.find_next_sibling("tr")
                    if next_row:
                        next_text = next_row.get_text()
                        md5_match = re.search(r'MD5:\s*([a-fA-F0-9]{32})', next_text)
                        if md5_match:
                            md5 = md5_match.group(1)
                
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
        """Get older MySQL versions from archives.
        
        For each accepted major version (e.g., 8.0, 8.4), fetches the latest 3 sub-versions.
        """
        resources = []
        
        try:
            url = "https://downloads.mysql.com/archives/community/"
            response = await self.http_client.get(url, headers=self.get_headers())
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find version select directly by ID (more reliable than label matching)
            version_select = soup.find("select", id="version")
            if not version_select:
                return resources
            
            options = version_select.find_all("option")
            accepted_versions = self.settings.get("mysql_accepted_versions", DEFAULT_ACCEPTED_VERSIONS)
            
            # Get all matching versions
            all_versions = [
                opt.get("value", opt.text).strip() for opt in options
                if any(opt.text.strip().startswith(av) for av in accepted_versions)
                and not any(c.isalpha() for c in opt.text.strip())
            ]
            
            # Group versions by major.minor and take latest 3 for each
            version_groups: dict[str, list[str]] = {}
            for version in all_versions:
                parts = version.split(".")
                if len(parts) >= 2:
                    major_minor = f"{parts[0]}.{parts[1]}"
                    if major_minor not in version_groups:
                        version_groups[major_minor] = []
                    version_groups[major_minor].append(version)
            
            # Select top 3 sub-versions for each major version
            selected_versions = []
            for major_minor in accepted_versions:
                if major_minor in version_groups:
                    # Versions should already be sorted descending from the dropdown
                    # Take the first 3 (latest)
                    selected_versions.extend(version_groups[major_minor][:3])
            
            for version in selected_versions:
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
