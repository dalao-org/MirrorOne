from typing import Tuple, List, Dict, Any

import httpx
from bs4 import BeautifulSoup
import re

NUMBER_OF_LEGACY_VERSIONS = 5


def nginx_version_handler(td: BeautifulSoup) -> dict:
    title = td.find("a").text
    try:
        latest_version = re.search(r"(?<=nginx-)(?P<v>\d+\.\d+\.\d+)", title).group("v")
        url = td.find("a")["href"]
        if url.startswith("/"):
            url = "https://nginx.org" + url
        pgp = td.find("a", string="pgp")["href"]
        if pgp.startswith("/"):
            pgp = "https://nginx.org" + pgp
        return {"version": latest_version, "url": url, "gpg": pgp, "file_name": f"nginx-{latest_version}.tar.gz"}
    except AttributeError:
        return None


def make_cache() -> tuple[list[dict], dict[str, str | Any]]:
    release_list = []
    latest_meta = {"version_file_name": "nginx_ver"}

    url = "https://nginx.org/en/download.html"
    soup = BeautifulSoup(httpx.get(url).content, "html.parser")

    # Latest version
    latest = soup.find("h4", string="Mainline version").parent.find_next_sibling("table").find_all("td")
    latest_version = None
    for td in latest:
        package_info = nginx_version_handler(td)
        if package_info:
            latest_version = package_info
            latest_meta["version"] = package_info["version"]
            break
    if latest_version:
        release_list.append(latest_version)
    else:
        raise RuntimeError("No latest Nginx version found.")

    # Legacy versions
    legacy_versions = soup.find("h4", string="Legacy versions").parent.find_next_siblings("table")
    legacy_versions = legacy_versions[0:NUMBER_OF_LEGACY_VERSIONS]
    for legacy in legacy_versions:
        td_list = legacy.find_all("td")
        for td in td_list:
            package_info = nginx_version_handler(td)
            if package_info:
                release_list.append(package_info)
                break

    return release_list, latest_meta
