"""
Lua Nginx module scraper.
"""
from .base import BaseScraper, Resource, ScrapeResult
from .registry import registry
from .github_utils import get_github_tags, filter_blacklist


@registry.register("lua_nginx_module")
class LuaNginxModuleScraper(BaseScraper):
    """Scraper for lua-nginx-module downloads."""
    
    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)
        
        # lua-nginx-module repo has no formal releases, only tags
        tags = await get_github_tags(
            self.http_client,
            "openresty",
            "lua-nginx-module",
            self.get_headers(),
            max_tags=10,
        )
        
        # Filter out rc/beta/alpha versions
        tags = filter_blacklist(tags)
        
        for tag in tags:
            version = tag.lstrip("v")
            result.resources.append(Resource(
                file_name=f"lua-nginx-module-{version}.tar.gz",
                url=f"https://github.com/openresty/lua-nginx-module/archive/refs/tags/{tag}.tar.gz",
                version=version,
            ))
        
        result.success = True
        return result
