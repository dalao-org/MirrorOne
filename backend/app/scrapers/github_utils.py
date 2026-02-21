"""
GitHub scraper utilities for common GitHub API operations.
"""
import re
from typing import Any
import httpx

from .base import Resource, VersionMeta

DEFAULT_BLACKLIST = ["rc", "beta", "alpha", "dev", "preview"]


async def get_github_releases(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    headers: dict[str, str],
    include_prerelease: bool = True,
    max_releases: int | None = None,
) -> list[dict[str, Any]]:
    """
    Get releases from a GitHub repository, with automatic pagination.
    
    Args:
        client: HTTP client
        owner: Repository owner
        repo: Repository name
        headers: Request headers
        include_prerelease: Whether to include prerelease versions
        max_releases: Maximum number of releases to return (None = fetch all pages)
        
    Returns:
        List of release dictionaries
    """
    base_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    all_releases: list[dict[str, Any]] = []
    page = 1

    while True:
        response = await client.get(
            base_url,
            headers=headers,
            params={"per_page": 100, "page": page},
        )
        response.raise_for_status()
        raw_releases = response.json()
        raw_count = len(raw_releases)

        if not raw_releases:
            break

        # Filter prereleases if needed
        if not include_prerelease:
            raw_releases = [r for r in raw_releases if not r.get("prerelease", False)]

        all_releases.extend(raw_releases)

        # If we already have enough, stop fetching more pages
        if max_releases is not None and len(all_releases) >= max_releases:
            break

        # GitHub returns fewer than per_page items on the last page
        if raw_count < 100:
            break

        page += 1

    # Limit results
    if max_releases is not None:
        all_releases = all_releases[:max_releases]

    return all_releases


async def get_github_tags(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    headers: dict[str, str],
    max_tags: int | None = None,
) -> list[str]:
    """
    Get tags from a GitHub repository.
    
    Args:
        client: HTTP client
        owner: Repository owner
        repo: Repository name
        headers: Request headers
        max_tags: Maximum number of tags to return (None = all)
        
    Returns:
        List of tag names (newest first)
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/tags"
    response = await client.get(url, headers=headers)
    response.raise_for_status()
    tags = response.json()
    tag_names = [tag["ref"].replace("refs/tags/", "") for tag in tags]
    
    # Reverse to get newest first
    tag_names.reverse()
    
    # Limit results
    if max_tags is not None:
        tag_names = tag_names[:max_tags]
    
    return tag_names


def filter_blacklist(items: list[str], blacklist: list[str] | None = None) -> list[str]:
    """Filter out items containing blacklist words.
    
    Args:
        items: List of items to filter
        blacklist: Optional custom blacklist, defaults to DEFAULT_BLACKLIST
    """
    if blacklist is None:
        blacklist = DEFAULT_BLACKLIST
    return [
        item for item in items
        if not any(word in item.lower() for word in blacklist)
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
    releases = await get_github_releases(
        client, owner, repo, headers,
        include_prerelease=False,
        max_releases=max_releases,
    )
    
    resources = []
    pattern = re.compile(regex)
    
    for release in releases:
        for asset in release.get("assets", []):
            if pattern.search(asset["name"]):
                resources.append(Resource(
                    file_name=asset["name"],
                    url=asset["browser_download_url"],
                    version=release["tag_name"],
                ))
    
    version_meta = None
    if latest_meta_key and resources:
        version_meta = VersionMeta(key=latest_meta_key, version=resources[0].version)
    
    return resources, version_meta
