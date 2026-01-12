import httpx
from bs4 import BeautifulSoup

ALLOWED_NUMBER_OF_VERSIONS = 5


def make_cache() -> list:
    resource_list = []

    url = "https://boostorg.jfrog.io/artifactory/main/release/"
    soup = BeautifulSoup(httpx.get(url).text, "html.parser")
    all_versions = soup.find_all("a", href=True)
    captured_version_numbers = []
    for v in all_versions:
        if v["href"].endswith("/") and "rc" not in v["href"] and ".." not in v["href"]:
            captured_version_numbers.append(v["href"].replace("/", ""))
    captured_version_numbers.sort(key=lambda s: list(map(int, s.split("."))))
    for version in captured_version_numbers[-ALLOWED_NUMBER_OF_VERSIONS:]:
        file_name = f"boost_{version.replace('.', '_')}.tar.gz"
        resource_list.append({
            "version": version,
            "url": f"https://boostorg.jfrog.io/artifactory/main/release/{version}/source/{file_name}",
            "file_name": file_name
        })
    return resource_list
