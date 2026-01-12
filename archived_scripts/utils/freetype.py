from typing import Tuple, List, Dict, Any

import httpx
from bs4 import BeautifulSoup
import re


def make_cache() -> tuple[list[dict[str, str | Any]], dict[str, str | Any]]:
    resource_list = []
    latest_meta = {"version_file_name": "freetype_ver"}

    url = "https://download.savannah.gnu.org/releases/freetype/"
    soup = BeautifulSoup(httpx.get(url).text, "html.parser")
    a_href_list = soup.find_all("a", href=True)
    for a in a_href_list:
        href = a["href"]
        re_result = re.search(r"(freetype-)(?P<v>\d+\.\d+\.\d+)(\.tar\.gz)", href)
        if re_result:
            version = re_result.group("v")
            resource_list.append({
                "url": f"https://download.savannah.gnu.org/releases/freetype/{href}",
                "file_name": href,
                "version": version
            })
    latest_meta["version"] = resource_list[0]["version"]
    return resource_list, latest_meta
