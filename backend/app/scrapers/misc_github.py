"""
Miscellaneous GitHub releases scraper.
Handles: jemalloc, lua-resty-core, lua-resty-lrucache, luajit2, lua-cjson, 
gperftools, icu4c, libzip, libsodium, argon2, libevent, webgrind, ngx_devel_kit, oniguruma
"""
import re
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


def _clean_version(version: str) -> str:
    """Strip non-numeric tag suffixes such as -RELEASE, -stable, -LTS, etc.

    Examples:
        '1.0.21-RELEASE' → '1.0.21'
        'v1.2.3-stable'  → '1.2.3'  (after lstrip('v') upstream)
        '1.18.0'         → '1.18.0' (unchanged)
    """
    m = re.match(r'^(\d[\d.]*)', version)
    return m.group(1).rstrip('.') if m else version


# Configuration for misc GitHub repos
# Each entry: (owner, repo, meta_key, file_pattern, file_name_prefix)
# - file_pattern: regex to match a release asset; None → use source tarball
# - file_name_prefix: override the filename stem used for source tarballs;
#   defaults to repo name when not provided / set to None.
MISC_REPOS = [
    # (owner, repo, meta_key, file_pattern, file_name_prefix)
    ("jemalloc", "jemalloc", "jemalloc_ver", r"jemalloc-.*\.tar\.bz2", None),
    ("openresty", "lua-resty-core", "lua_resty_core_ver", None, None),
    ("openresty", "lua-resty-lrucache", "lua_resty_lrucache_ver", None, None),
    ("openresty", "luajit2", "luajit2_ver", None, None),
    ("openresty", "lua-cjson", "lua_cjson_ver", None, None),
    ("gperftools", "gperftools", None, r"gperftools-\d+\.\d+\.tar\.gz", None),
    ("unicode-org", "icu", "icu4c_ver", r"icu4c-.*-(?:src|sources?)\.tgz", None),
    ("nih-at", "libzip", "libzip_ver", r"libzip-.*\.tar\.gz", None),
    ("jedisct1", "libsodium", "libsodium_ver", r"libsodium-.*\.tar\.gz", None),
    # The GitHub repo is "phc-winner-argon2" but LNMP expects "argon2-{ver}.tar.gz"
    ("P-H-C", "phc-winner-argon2", "argon2_ver", None, "argon2"),
    ("libevent", "libevent", None, r"libevent-.*\.tar\.gz", None),
    ("vision5", "ngx_devel_kit", None, None, None),
    ("kkos", "oniguruma", None, r"onig-.*\.tar\.gz", None),
]


@registry.register("misc_github")
class MiscGithubScraper(BaseScraper):
    """Scraper for miscellaneous GitHub releases."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        # Read unified max_versions from settings; 0 means fetch all (pass None to API helper)
        max_versions_setting: int = self.settings.get("misc_github_max_versions", 5)
        max_releases: int | None = max_versions_setting if max_versions_setting > 0 else None
        
        for owner, repo, meta_key, file_pattern, file_name_prefix in MISC_REPOS:
            try:
                await self._scrape_repo(
                    owner, repo, meta_key, file_pattern, file_name_prefix, max_releases, result
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
        file_name_prefix: str | None,
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
            version = _clean_version(tag.lstrip("v"))
            assets = release.get("assets", [])
            
            if file_pattern and assets:
                # Collect ALL matching assets per release (some projects like libsodium
                # publish multiple tarballs per release, e.g. mingw + regular .tar.gz)
                pattern = re.compile(file_pattern)
                matched_any = False
                for asset in assets:
                    name = asset.get("name", "")
                    if pattern.search(name):
                        result.resources.append(Resource(
                            file_name=name,
                            url=asset["browser_download_url"],
                            version=version,
                        ))
                        matched_any = True
                if matched_any and latest_version is None:
                    latest_version = version
            else:
                # Use source tarball; allow a custom prefix to override the repo name
                # (e.g. argon2: repo="phc-winner-argon2" but expected name is "argon2-…")
                prefix = file_name_prefix if file_name_prefix else repo
                file_name = f"{prefix}-{version}.tar.gz"
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
