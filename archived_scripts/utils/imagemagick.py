from typing import Tuple, List, Dict, Any

import httpx
from bs4 import BeautifulSoup


def make_cache() -> tuple[list[dict[str, str | Any]], dict[str, str | Any]]:
    url = "https://imagemagick.org/archive/"
    soup = BeautifulSoup(httpx.get(url).text, "html.parser")
    resource_list = []
    latest_meta = {"version_file_name": "imagemagick_ver"}

    for a in soup.find_all("a", href=True):
        if a["href"].startswith("ImageMagick-") and a["href"].endswith(".tar.gz"):
            resource_list.append({
                "version": a["href"].replace("ImageMagick-", "").replace(".tar.gz", ""),
                "url": url + a["href"],
                "gpg": url + a["href"] + ".asc",
                "file_name": a["href"].split("/")[-1]
            })
    latest_meta["version"] = resource_list[0]["version"]
    return resource_list, latest_meta
