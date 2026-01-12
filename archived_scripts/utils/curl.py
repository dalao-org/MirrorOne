from typing import Tuple, List, Dict, Any

import httpx
from bs4 import BeautifulSoup


def make_cache() -> tuple[list[dict[str, str | Any]], dict[str, str | Any]]:
    version_list = []
    latest_meta = {"version_file_name": "curl_ver"}

    curl_release_page = httpx.get("https://curl.se/download/").content
    curl_release_bs = BeautifulSoup(curl_release_page, "html.parser")
    releases_bs_list = curl_release_bs.find("table", class_="daily").find_all("tr", class_=["even", "odd"])
    for release_bs in releases_bs_list:
        version_num = release_bs.find_all("td")[0].text
        for value in release_bs.find_all("td"):
            try:
                url = value.find("a")["href"]
            except TypeError:
                continue
            if ".tar.gz" in url:
                if not url.startswith("https://") and not url.startswith("http://"):
                    url = "https://curl.se/" + url
                version_list.append({
                    "version": version_num,
                    "url": url,
                    "file_name": url.split("/")[-1],
                    "gpg": url + ".asc"})
    latest_meta["version"] = version_list[0]["version"]
    return version_list, latest_meta
