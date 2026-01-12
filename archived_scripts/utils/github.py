from typing import Tuple, List, Dict, Any

import httpx
import re

BLACKLIST_WORD = ["rc", "beta", "alpha"]


def download_repo_by_tag(owner_name: str, repo_name: str, archive_type: str = "tar.gz",
                         filter_blacklist: bool = True, latest_meta_name: str = None) -> tuple[list[dict[str, str | Any]], dict[str, str | Any]]:
    """
    Download repository archive by tag

    This function will list all repository tags and download them one by one

    This function is suitable for GitHub repositories that does not make any releases and package is
    repository content itself

    :param latest_meta_name: Package name for latest meta returning
    :param owner_name: GitHub account name
    :param repo_name: repository name, e.g. "alibaba/tengine"
    :param archive_type: "tar.gz" or "zip"
    :param filter_blacklist: Boolean of trigger if filter blacklist word in tag name
    :return: list of dict, each dict contains at least "url" and "file_name"
    """
    if archive_type not in ["tar.gz", "zip"]:
        raise ValueError("archive_type must be 'tar.gz' or 'zip'")

    resource_list = []

    url = f"https://api.github.com/repos/{owner_name}/{repo_name}/git/refs/tags"
    if filter_blacklist:
        tag_list = [tag["ref"].replace("refs/tags/", "") for tag in httpx.get(url).json()
                    if not any(w in tag["ref"] for w in BLACKLIST_WORD)]
    else:
        tag_list = [tag["ref"].replace("refs/tags/", "") for tag in httpx.get(url).json()]
    for tag in tag_list:
        tag_archive_url = f"https://github.com/{owner_name}/{repo_name}/archive/refs/tags/{tag}.{archive_type}"
        resource_list.append({
            "url": tag_archive_url,
            "file_name": f"{repo_name}-{tag}.{archive_type}",
            "version": tag
        })
    resource_list.reverse()
    if latest_meta_name:
        latest_meta = {"version_file_name": latest_meta_name, "version": resource_list[0]["version"]}
    else:
        latest_meta = None
    return resource_list, latest_meta


def get_single_package_from_release(owner_name: str, repo_name: str, latest_meta_name: str = None) -> tuple[list[dict[str, str | Any]], dict[str, str | None | Any] | None]:
    """
    Get single package from GitHub release

    This function will get release and download the package

    This function is suitable for GitHub repositories that make releases and only one file in each release

    :param latest_meta_name: Package name for latest meta returning
    :param owner_name: GitHub account name
    :param repo_name: repository name, e.g. "alibaba/tengine"
    :return: list of dict, each dict contains at least "url" and "file_name"
    """
    resource_list = []
    url = f"https://api.github.com/repos/{owner_name}/{repo_name}/releases"
    releases = httpx.get(url).json()
    for release in releases:
        if len(release["assets"]) == 1:
            if any(w in release["assets"][0]["name"] for w in BLACKLIST_WORD):
                continue
            resource_list.append({
                "url": release["assets"][0]["browser_download_url"],
                "file_name": release["assets"][0]["name"],
                "version": release["tag_name"]
            })
        else:
            raise ValueError("More than one file in release")
    if latest_meta_name:
        latest_meta = {"version_file_name": latest_meta_name, "version": resource_list[0]["version"]}
    else:
        latest_meta = None
    return resource_list, latest_meta


def get_package_from_release_with_regular_expression(owner_name: str, repo_name: str, regex: str, max_asset: int = 0,
                                                     latest_meta_name: str = None) -> tuple[list[dict[str, Any]], dict[str, str | None | Any] | None]:
    """
    Get single package from GitHub release with regular expression

    This function will get release and download the package

    This function is suitable for GitHub repositories that make releases and only one file in each release

    :param latest_meta_name: Package name for latest meta returning
    :param owner_name: GitHub account name
    :param repo_name: repository name, e.g. "alibaba/tengine"
    :param regex: regular expression to match file name
    :param max_asset: Maximum number of assets to cache
    :return: list of dict, each dict contains at least "url" and "file_name"
    """
    if regex is None:
        raise ValueError("regex must be specified")

    resource_list = []
    url = f"https://api.github.com/repos/{owner_name}/{repo_name}/releases"
    releases = httpx.get(url).json()
    non_pre_release = [release for release in releases if not release["prerelease"]]
    for release in non_pre_release:
        for asset in release["assets"]:
            if re.search(regex, asset["name"]):
                resource_list.append({
                    "url": asset["browser_download_url"],
                    "file_name": asset["name"],
                    "version": release["tag_name"]
                })
    if len(resource_list) == 0:
        raise ValueError("No asset matches regex")

    if latest_meta_name:
        latest_meta = {"version_file_name": latest_meta_name, "version": resource_list[0]["version"]}
    else:
        latest_meta = None

    if max_asset > 0:
        return resource_list[:max_asset], latest_meta
    else:
        return resource_list, latest_meta
