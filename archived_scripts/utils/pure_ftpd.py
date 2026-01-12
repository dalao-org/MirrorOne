from bs4 import BeautifulSoup
from http_utils import httpx_get_request


def make_cache() -> list:
    url = "https://ftp.pureftpd.org/public/public/pure-ftpd/releases/"
    try:
        response = httpx_get_request(url)
    except RuntimeError:
        return []
    soup = BeautifulSoup(response.text, "html.parser")

    resource_list = []
    for a in soup.find_all("a", href=True):
        if a["href"].endswith(".tar.gz") and a["href"].startswith("pure-ftpd-"):
            resource_list.append({
                "url": url + a["href"],
                "file_name": a["href"]
            })
    return resource_list
