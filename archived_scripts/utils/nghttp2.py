from typing import Tuple, List, Dict, Any

import httpx


def make_cache() -> tuple[list[dict[str, str | Any]], dict[str, str | Any]]:
    release_list = []
    latest_meta = {"version_file_name": "nghttp2_ver"}

    url = "https://api.github.com/repos/nghttp2/nghttp2/releases"
    response = httpx.get(url).json()
    non_pre_releases = [release for release in response if not release["prerelease"]][:10]

    for release in non_pre_releases:
        for asset in release["assets"]:
            if "tar.gz" in asset["name"]:
                release_list.append({
                    "version": release["tag_name"].replace("v", "") if release["tag_name"].startswith("v") else release["tag_name"],
                    "url": asset["browser_download_url"],
                    "file_name": asset["name"],
                    "gpg": asset["browser_download_url"] + ".asc",
                    "md5": "/".join(asset["browser_download_url"].split("/")[:-1]) + "/checksums.txt"
                })

    latest_meta["version"] = release_list[0]["version"]
    return release_list, latest_meta
