"""
GitHub scraper utilities for common GitHub API operations.
"""
import re
from typing import Any
import httpx

from .base import Resource, VersionMeta

BLACKLIST_WORDS = ["rc", "beta", "alpha", "dev", "preview"]


async def get_github_releases(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    headers: dict[str, str],
) -> list[dict[str, Any]]:
    """
    Get releases from a GitHub repository.
    
    Args:
        client: HTTP client
        owner: Repository owner
        repo: Repository name
        headers: Request headers
        
    Returns:
        List of release dictionaries
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


async def get_github_tags(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    headers: dict[str, str],
) -> list[str]:
    """
    Get tags from a GitHub repository.
    
    Args:
        client: HTTP client
        owner: Repository owner
        repo: Repository name
        headers: Request headers
        
    Returns:
        List of tag names
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/tags"
    response = await client.get(url, headers=headers)
    response.raise_for_status()
    tags = response.json()
    return [tag["ref"].replace("refs/tags/", "") for tag in tags]


def filter_blacklist(items: list[str]) -> list[str]:
    """Filter out items containing blacklist words."""
    return [
        item for item in items
        if not any(word in item.lower() for word in BLACKLIST_WORDS)
    ]


async def download_repo_by_tag(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    headers: dict[str, str],
    archive_type: str = "tar.gz",
    filter_bl: bool = True,
    latest_meta_key: str | None = None,
) -> tuple[list[Resource], VersionMeta | None]:
    """
    Get download URLs for repository archives by tag.
    
    Args:
        client: HTTP client
        owner: Repository owner
        repo: Repository name
        headers: Request headers
        archive_type: "tar.gz" or "zip"
        filter_bl: Whether to filter blacklist words
        latest_meta_key: Key for version meta (e.g., "nginx_ver")
        
    Returns:
        Tuple of (resources list, version meta or None)
    """
    tags = await get_github_tags(client, owner, repo, headers)
    
    if filter_bl:
        tags = filter_blacklist(tags)
    
    resources = []
    for tag in reversed(tags):  # Oldest first
        url = f"https://github.com/{owner}/{repo}/archive/refs/tags/{tag}.{archive_type}"
        resources.append(Resource(
            file_name=f"{repo}-{tag}.{archive_type}",
            url=url,
            version=tag,
        ))
    
    resources.reverse()  # Newest first
    
    version_meta = None
    if latest_meta_key and resources:
        version_meta = VersionMeta(key=latest_meta_key, version=resources[0].version)
    
    return resources, version_meta


async def get_packages_from_release(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    headers: dict[str, str],
    regex: str,
    max_releases: int = 5,
    latest_meta_key: str | None = None,
) -> tuple[list[Resource], VersionMeta | None]:
    """
    Get packages from GitHub releases matching a regex pattern.
    
    Args:
        client: HTTP client
        owner: Repository owner
        repo: Repository name
        headers: Request headers
        regex: Regex pattern to match asset names
        max_releases: Maximum number of releases to include
        latest_meta_key: Key for version meta
        
    Returns:
        Tuple of (resources list, version meta or None)
    """
    releases = await get_github_releases(client, owner, repo, headers)
    
    # Filter out prereleases
    releases = [r for r in releases if not r.get("prerelease", False)]
    
    resources = []
    pattern = re.compile(regex)
    
    release_count = 0
    for release in releases:
        if release_count >= max_releases:
            break
        
        for asset in release.get("assets", []):
            if pattern.search(asset["name"]):
                resources.append(Resource(
                    file_name=asset["name"],
                    url=asset["browser_download_url"],
                    version=release["tag_name"],
                ))
        
        release_count += 1
    
    version_meta = None
    if latest_meta_key and resources:
        version_meta = VersionMeta(key=latest_meta_key, version=resources[0].version)
    
    return resources, version_meta
