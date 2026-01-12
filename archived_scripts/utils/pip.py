import httpx
from bs4 import BeautifulSoup

BLACK_LIST_WORD = ["test", "b1", "b2", "b3"]
ALLOWED_NUMBER_OF_VERSIONS = 5


def make_cache() -> list:
    release_list = []
    url = "https://src.fedoraproject.org/repo/pkgs/python-pip/"
    soup = BeautifulSoup(httpx.get(url).text, "html.parser")
    href_list = soup.find_all("a", href=True)
    resource_list = []
    for resource in href_list:
        if (resource["href"].endswith(".tar.gz/") and not any(word in resource["href"] for word in BLACK_LIST_WORD)
                and resource["href"].startswith("pip-")):
            resource_list.append(resource["href"])
    resource_list.reverse()
    resource_list = resource_list[:ALLOWED_NUMBER_OF_VERSIONS]
    for resource in resource_list:
        package_name = resource.replace("/", "")
        sha512_page_url = f"https://src.fedoraproject.org/repo/pkgs/python-pip/{resource}sha512/"
        page_soup = BeautifulSoup(httpx.get(sha512_page_url).text, "html.parser")
        sha512_folder = page_soup.find_all("a", href=True)
        sha512_text = ""
        for sha512_file in sha512_folder:
            if sha512_file["href"].endswith("/") and sha512_file.text.endswith("..>"):
                sha512_text = sha512_file["href"].replace("/", "")
                break
        release_list.append({
            "version": resource.replace("pip-", "").replace(".tar.gz/", ""),
            "file_name": package_name,
            "url": f"https://src.fedoraproject.org/repo/pkgs/python-pip/{resource}sha512/{sha512_text}/{package_name}",
            "sha512": sha512_text
        })
    return release_list
