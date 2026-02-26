"""
GNU Binutils scraper.
Source: https://ftp.gnu.org/gnu/binutils/

Collects all tarball formats (gz, bz2, xz, zst) for standard binutils releases.
The -with-gold- variants and .sig signature files are intentionally excluded.
"""
import re
from bs4 import BeautifulSoup

from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry


_BASE_URL = "https://ftp.gnu.org/gnu/binutils/"

# Matches: binutils-2.46.0.tar.gz / .bz2 / .xz / .zst
# Does NOT match: binutils-with-gold-*, *.sig, *.patch.gz, README-*
_FILE_PATTERN = re.compile(
    r"^binutils-(\d[\d.]*)\.tar\.(gz|bz2|xz|zst)$"
)


def _version_key(version: str) -> tuple:
    """Turn '2.46.0' into (2, 46, 0) for proper numeric sorting."""
    try:
        return tuple(int(x) for x in version.split("."))
    except ValueError:
        return (0,)


@registry.register("binutils")
class BinutilsScraper(BaseScraper):
    """Scraper for GNU Binutils downloads."""

    async def scrape(self) -> ScrapeResult:
        result = ScrapeResult(scraper_name=self.name)

        max_versions: int = self.settings.get("binutils_max_versions", 5)

        response = await self.http_client.get(_BASE_URL, headers=self.get_headers())
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Collect all matching files, grouped by version
        # version -> list of (href, ext)
        versions: dict[str, list[str]] = {}
        for link in soup.find_all("a", href=True):
            href: str = link["href"]
            m = _FILE_PATTERN.match(href)
            if m:
                ver = m.group(1)
                versions.setdefault(ver, []).append(href)

        # Sort versions descending (newest first) and take the top N
        sorted_versions = sorted(versions.keys(), key=_version_key, reverse=True)
        selected = sorted_versions[:max_versions]

        latest_version: str | None = selected[0] if selected else None

        for ver in selected:
            for href in sorted(versions[ver]):  # stable order within a version
                result.resources.append(Resource(
                    file_name=href,
                    url=_BASE_URL + href,
                    version=ver,
                ))

        if latest_version:
            result.version_metas.append(
                VersionMeta(key="binutils_ver", version=latest_version)
            )

        result.success = True
        return result
