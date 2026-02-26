"""
GraphicsMagick scraper.
Source: SourceForge project files API
https://sourceforge.net/projects/graphicsmagick/files/graphicsmagick/
"""
import re

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


def _version_key(version: str) -> tuple:
    try:
        return tuple(int(x) for x in version.split("."))
    except ValueError:
        return (0,)


@registry.register("graphicsmagick")
class GraphicsMagickScraper(BaseScraper):
    """Scraper for GraphicsMagick downloads via SourceForge."""

    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)

        max_versions: int = self.settings.get("graphicsmagick_max_versions", 5)

        # SourceForge JSON API returns directory/file listing
        api_url = "https://sourceforge.net/projects/graphicsmagick/files/graphicsmagick/?format=json"
        response = await self.http_client.get(
            api_url,
            headers={**self.get_headers(), "Accept": "application/json"},
            timeout=30.0,
            follow_redirects=True,
        )
        response.raise_for_status()

        data = response.json()

        # Each entry with type="directory" and a version-like name is a release
        _ver_re = re.compile(r"^\d+\.\d+")
        versions: list[str] = [
            entry["name"]
            for entry in data.get("files", [])
            if entry.get("type") == "directory" and _ver_re.match(entry.get("name", ""))
        ]

        versions.sort(key=_version_key, reverse=True)
        selected = versions[:max_versions]

        for ver in selected:
            for ext in ("tar.gz", "tar.bz2", "tar.xz", "tar.lz"):
                file_name = f"GraphicsMagick-{ver}.{ext}"
                dl_url = (
                    f"https://downloads.sourceforge.net/project/"
                    f"graphicsmagick/graphicsmagick/{ver}/{file_name}"
                )
                result.resources.append(Resource(
                    file_name=file_name,
                    url=dl_url,
                    version=ver,
                ))

        if selected:
            result.version_metas.append(
                VersionMeta(key="graphicsmagick_ver", version=selected[0])
            )

        result.success = True
        return result
