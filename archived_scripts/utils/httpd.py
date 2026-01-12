from typing import Tuple, List, Dict

import httpx
from bs4 import BeautifulSoup

ALLOWED_NUMBER_OF_VERSIONS = 5
BLACK_LIST_WORD = ["alpha", "beta", "deps", "rc"]


def make_cache() -> tuple[list[dict[str, str]], dict[str, str]]:
    resource_list = []
    latest_meta = {"version_file_name": "apache_ver"}

    url = "https://archive.apache.org/dist/httpd/"
    soup = BeautifulSoup(httpx.get(url).text, "html.parser")
    file_list = []
    for a in soup.find_all("a"):
        if a.text.startswith("httpd-") and a.text.endswith(".tar.gz"):
            if not any(word for word in BLACK_LIST_WORD if word in a.text):
                file_list.append(a.text.replace(".tar.gz", "").replace("httpd-", ""))
    file_list.sort(key=lambda x: [int(c) for c in x.split(".")])
    file_list.reverse()
    file_list = file_list[:ALLOWED_NUMBER_OF_VERSIONS]
    for file in file_list:
        resource_list.append(
            {
                "url": f"https://archive.apache.org/dist/httpd/httpd-{file}.tar.gz",
                "file_name": f"httpd-{file}.tar.gz",
                "version": file,
                "gpg": f"https://archive.apache.org/dist/httpd/httpd-{file}.tar.gz.asc",
                "sha256": f"https://archive.apache.org/dist/httpd/httpd-{file}.tar.gz.sha256",
                "sha512": f"https://archive.apache.org/dist/httpd/httpd-{file}.tar.gz.sha512",
            }
        )
    latest_meta["version"] = resource_list[0]["version"]
    return resource_list, latest_meta
