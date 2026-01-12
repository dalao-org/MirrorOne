from typing import Tuple, List, Dict, Any

import httpx
from bs4 import BeautifulSoup
import re


def make_cache() -> tuple[list[dict[str, str | Any]], dict[str, str | Any]]:
    resource_list = []
    latest_meta = {"version_file_name": "libiconv_ver"}

    url = "https://ftp.gnu.org/gnu/libiconv/"
    soup = BeautifulSoup(httpx.get(url).text, "html.parser")
    a_href_list = soup.find_all("a", href=re.compile(r"libiconv-\d+\.\d+(\.\d+)?\.tar\.gz$"))
    for a in a_href_list:
        resource_list.append({
            "url": url + a["href"],
            "file_name": a["href"],
            "version": a["href"].replace("libiconv-", "").replace(".tar.gz", "")
        })
    latest_meta["version"] = resource_list[0]["version"]
    return resource_list, latest_meta
