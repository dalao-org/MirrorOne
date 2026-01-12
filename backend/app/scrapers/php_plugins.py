"""
PHP PECL plugins scraper.
Handles: apcu, imagick, swoole, xdebug, mongodb, memcache, yaf, gmagick, mongo
"""
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry

DEFAULT_BLACKLIST = ["alpha", "beta", "rc", "test"]

# PHP PECL packages to scrape
PECL_PACKAGES = [
    # (package_name, file_prefix, meta_key, allow_unstable)
    ("apcu", "apcu", "apcu_ver", False),
    ("imagick", "imagick", "imagick_ver", False),
    ("swoole", "swoole", "swoole_ver", False),
    ("xdebug", "xdebug", "xdebug_ver", False),
    ("mongodb", "mongodb", "pecl_mongodb_ver", False),
    ("memcache", "memcache", "pecl_memcache_ver", False),
    ("yaf", "yaf", "yaf_ver", False),
    ("gmagick", "gmagick", "gmagick_ver", True),
    ("mongo", "mongo", "pecl_mongo_ver", False),
]


@registry.register("php_plugins")
class PhpPluginsScraper(BaseScraper):
    """Scraper for PHP PECL extensions."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        blacklist = self.settings.get("php_plugins_blacklist", DEFAULT_BLACKLIST)
        
        for package_name, file_prefix, meta_key, allow_unstable in PECL_PACKAGES:
            try:
                await self._scrape_pecl_package(
                    package_name, file_prefix, meta_key, allow_unstable, blacklist, result
                )
            except Exception as e:
                # Log but continue with other packages
                pass
        
        result.success = True
        return result
    
    async def _scrape_pecl_package(
        self,
        package_name: str,
        file_prefix: str,
        meta_key: str,
        allow_unstable: bool,
        blacklist: list[str],
        result: ScrapeResult,
    ) -> None:
        """Scrape a single PECL package."""
        url = f"https://pecl.php.net/package/{package_name}"
        
        response = await self.http_client.get(
            url,
            headers={
                **self.get_headers(),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        latest_version = None
        
        for link in soup.find_all("a"):
            text = link.text
            href = link.get("href", "")
            
            if text.startswith(f"{file_prefix}-") and text.endswith(".tgz"):
                # Filter unstable versions
                if not allow_unstable and any(word in text.lower() for word in blacklist):
                    continue
                
                version = text.replace(f"{file_prefix}-", "").replace(".tgz", "")
                download_url = f"https://pecl.php.net{href}" if href.startswith("/") else href
                
                result.resources.append(Resource(
                    file_name=text,
                    url=download_url,
                    version=version,
                ))
                
                if latest_version is None:
                    latest_version = version
        
        # Add version meta
        if latest_version:
            result.version_metas.append(
                VersionMeta(key=meta_key, version=latest_version)
            )
