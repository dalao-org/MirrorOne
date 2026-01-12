from typing import Tuple, List, Dict, Any

import httpx


ALLOWED_NUMBER_OF_RELEASES = 3


def make_cache() -> tuple[list[dict[str, str | Any]], dict[str, str | Any]]:
    release_list = []
    latest_meta = {"version_file_name": "openresty_ver"}

    url = "https://api.github.com/repos/openresty/openresty/releases"
    response = httpx.get(url).json()
    non_pre_releases = [release for release in response if not release["prerelease"]]
    non_pre_releases = [r["name"].replace("v", "") for r in non_pre_releases[:ALLOWED_NUMBER_OF_RELEASES]]
    for release in non_pre_releases:
        release_list.append({
            "version": release,
            "file_name": f"openresty-{release}.tar.gz",
            "url": f"https://openresty.org/download/openresty-{release}.tar.gz",
            "pgp": f"https://openresty.org/download/openresty-{release}.tar.gz.asc"
        })
    latest_meta["version"] = release_list[0]["version"]
    return release_list, latest_meta
