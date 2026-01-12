from typing import Tuple, List, Dict, Any

import httpx
from bs4 import BeautifulSoup


def make_cache() -> tuple[list[dict[str, Any]], list[dict[str, str] | dict[str, str]]]:
    release_list = []
    latest_meta = [{"version_file_name": "phpmyadmin_ver"}, {"version_file_name": "phpmyadmin_oldver"}]

    release_page = httpx.get("https://www.phpmyadmin.net/downloads/").content
    release_page = BeautifulSoup(release_page, "html.parser")
    releases_download_table = release_page.find_all("table", class_="table-condensed")
    for release in releases_download_table:
        this_version_dl_list = release.find("tbody").find_all("tr")
        for resource in this_version_dl_list:
            if ".tar.gz" in resource.text and "all-languages" in resource.text:
                if "snapshot" not in resource.text and "latest" not in resource.text:
                    download_metadata = resource.find_all("td")[0].find("a")
                    url = download_metadata["href"]
                    version = download_metadata.text.replace("phpMyAdmin-", "").replace("-all-languages.tar.gz", "")
                    sha256 = download_metadata["data-sha256"]
                    release_list.append({"version": version, "url": url, "sha256": sha256,
                                         "file_name": url.split("/")[-1]})
    latest_meta[0]["version"] = release_list[0]["version"]
    latest_meta[1]["version"] = release_list[1]["version"]
    return release_list, latest_meta
