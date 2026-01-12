"""
Lua Nginx module scraper.
"""
from .base import BaseScraper, Resource, ScrapeResult
from .registry import registry
from .github_utils import get_github_releases


@registry.register("lua_nginx_module")
class LuaNginxModuleScraper(BaseScraper):
    """Scraper for lua-nginx-module downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        releases = await get_github_releases(
            self.http_client,
            "openresty",
            "lua-nginx-module",
            self.get_headers(),
            include_prerelease=False,
            max_releases=5,
        )
        
        for release in releases:
            version = release["tag_name"].lstrip("v")
            result.resources.append(Resource(
                file_name=f"lua-nginx-module-{version}.tar.gz",
                url=f"https://github.com/openresty/lua-nginx-module/archive/refs/tags/{release['tag_name']}.tar.gz",
                version=version,
            ))
        
        result.success = True
        return result
