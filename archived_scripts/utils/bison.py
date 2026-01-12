import httpx
from bs4 import BeautifulSoup
import re

ALLOWED_NUMBER_OF_VERSIONS = 5


def make_cache() -> list:
    resource_list = []
    url = "https://ftp.gnu.org/gnu/bison/"
    soup = BeautifulSoup(httpx.get(url).text, "html.parser")
    a_href_list = soup.find_all("a", href=re.compile(r"bison-\d+\.\d+(\.\d+)?\.tar\.gz$"))
    for a_href in a_href_list:
        resource_list.append({
            "url": url + a_href["href"],
            "file_name": a_href["href"],
            "version": a_href["href"].replace("bison-", "").replace(".tar.gz", "")
        })
    sorted_list = sorted(resource_list, key=lambda x: x["version"])
    sorted_list.reverse()
    return sorted_list[:ALLOWED_NUMBER_OF_VERSIONS]
