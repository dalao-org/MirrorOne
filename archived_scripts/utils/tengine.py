from typing import Tuple, List, Dict, Any

import httpx


def make_cache() -> tuple[list[dict[str, str | Any]], dict[str, str | Any]]:
    resource_list = []
    latest_meta = {"version_file_name": "tengine_ver"}

    url = "https://api.github.com/repos/alibaba/tengine/releases"
    full_release_list = httpx.get(url).json()
    non_pre_release_list = [release for release in full_release_list if not release["prerelease"]]
    tag_list = [release["tag_name"] for release in non_pre_release_list]
    for tag in tag_list:
        tag_tar_gz = f"https://github.com/alibaba/tengine/archive/refs/tags/{tag}.tar.gz"
        resource_list.append({
            "version": tag,
            "url": tag_tar_gz,
            "file_name": f"tengine-{tag}.tar.gz"
        })
    latest_meta["version"] = resource_list[0]["version"]
    return resource_list, latest_meta
