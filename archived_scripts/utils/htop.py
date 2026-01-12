import httpx
from bs4 import BeautifulSoup

ALLOWED_NUMBER_OF_VERSIONS = 5


def make_cache() -> list:
    release_list = []
    url = "https://src.fedoraproject.org/repo/pkgs/htop/"
    soup = BeautifulSoup(httpx.get(url).text, "html.parser")
    version_list = []
    for a in soup.find_all("a", href=True):
        if a["href"].endswith(".tar.gz/"):
            version_list.append(a["href"])
    version_list.sort(reverse=True)
    version_list = version_list[:ALLOWED_NUMBER_OF_VERSIONS]
    for version in version_list:
        sub_url = url + version + "sha512/"
        package_name = version.replace("/", "")
        soup = BeautifulSoup(httpx.get(sub_url).text, "html.parser")
        a_href_list = soup.find_all("a", href=True)
        hash_url = ""
        for a in a_href_list:
            if a.text.endswith("..>"):
                hash_url = a["href"]
                break
        release_list.append({
            "file_name": package_name,
            "url": sub_url + hash_url + package_name
        })
    return release_list
