"""
Miscellaneous GitHub releases scraper.
Handles: jemalloc, lua-resty-core, lua-resty-lrucache, luajit2, lua-cjson, 
gperftools, icu4c, libzip, libsodium, argon2, libevent, webgrind, ngx_devel_kit, oniguruma
"""
import re
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


# Configuration for misc GitHub repos
MISC_REPOS = [
    # (owner, repo, meta_key, file_pattern)
    ("jemalloc", "jemalloc", "jemalloc_ver", r"jemalloc-.*\.tar\.bz2"),
    ("openresty", "lua-resty-core", "lua_resty_core_ver", None),
    ("openresty", "lua-resty-lrucache", "lua_resty_lrucache_ver", None),
    ("openresty", "luajit2", "luajit2_ver", None),
    ("openresty", "lua-cjson", "lua_cjson_ver", None),
    ("gperftools", "gperftools", None, r"gperftools-\d+\.\d+\.tar\.gz"),
    ("unicode-org", "icu", "icu4c_ver", r"icu4c-.*-(?:src|sources?)\.tgz"),
    ("nih-at", "libzip", "libzip_ver", r"libzip-.*\.tar\.gz"),
    ("jedisct1", "libsodium", "libsodium_ver", r"libsodium-.*\.tar\.gz"),
    ("P-H-C", "phc-winner-argon2", "argon2_ver", None),
    ("libevent", "libevent", None, r"libevent-.*\.tar\.gz"),
    ("vision5", "ngx_devel_kit", None, None),
    ("kkos", "oniguruma", None, r"onig-.*\.tar\.gz"),
]


@registry.register("misc_github")
class MiscGithubScraper(BaseScraper):
    """Scraper for miscellaneous GitHub releases."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        # Read unified max_versions from settings; 0 means fetch all (pass None to API helper)
        max_versions_setting: int = self.settings.get("misc_github_max_versions", 5)
        max_releases: int | None = max_versions_setting if max_versions_setting > 0 else None
        
        for owner, repo, meta_key, file_pattern in MISC_REPOS:
            try:
                await self._scrape_repo(
                    owner, repo, meta_key, file_pattern, max_releases, result
                )
            except Exception:
                # Intentionally continue with other repos - one failed repo shouldn't stop others
                continue
        
        result.success = True
        return result
    
    async def _scrape_repo(
        self,
        owner: str,
        repo: str,
        meta_key: str | None,
        file_pattern: str | None,
        max_releases: int | None,
        result: ScrapeResult,
    ) -> None:
        """Scrape a single GitHub repo."""
        releases = await get_github_releases(
            self.http_client,
            owner,
            repo,
            self.get_headers(),
            include_prerelease=False,
            max_releases=max_releases,
        )
        
        latest_version = None
        
        for release in releases:
            tag = release["tag_name"]
            version = tag.lstrip("v")
            assets = release.get("assets", [])
            
            if file_pattern and assets:
                # Look for matching asset
                pattern = re.compile(file_pattern)
                for asset in assets:
                    name = asset.get("name", "")
                    if pattern.search(name):
                        result.resources.append(Resource(
                            file_name=name,
                            url=asset["browser_download_url"],
                            version=version,
                        ))
                        if latest_version is None:
                            latest_version = version
                        break
            else:
                # Use source tarball
                file_name = f"{repo}-{version}.tar.gz"
                result.resources.append(Resource(
                    file_name=file_name,
                    url=f"https://github.com/{owner}/{repo}/archive/refs/tags/{tag}.tar.gz",
                    version=version,
                ))
                if latest_version is None:
                    latest_version = version
        
        # Add version meta if specified
        if meta_key and latest_version:
            result.version_metas.append(
                VersionMeta(key=meta_key, version=latest_version)
            )
