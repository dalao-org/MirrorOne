import httpx
from bs4 import BeautifulSoup

ACCEPTED_VERSIONS = ["5.3", "5.4", "5.5", "5.6", "7.0", "7.1", "7.2", "7.3", "7.4", "8.0", "8.1", "8.2", "8.3"]


def older_php_cache_maker() -> list:
    version_list = []
    php_release_page = httpx.get("https://www.php.net/releases/").content
    php_release_bs = BeautifulSoup(php_release_page, "html.parser")
    releases_bs_list = php_release_bs.find_all("li")
    for release_bs in releases_bs_list:
        if "(tar.gz)" in release_bs.text and "Download" not in release_bs.text:
            metadata = release_bs.text.split(" ")
            if len(metadata) == 4:
                version_num = metadata[1]
                sha256 = metadata[3].replace("\n", "")
                url = release_bs.find("a")["href"]
                if url.startswith("/"):
                    url = "https://www.php.net" + url
                version_list.append({"version": version_num, "url": url, "sha256": sha256,
                                     "file_name": url.split("/")[-1]})
    return version_list


def latest_php_cache_maker() -> list:
    version_list = []
    php_release_page = httpx.get("https://www.php.net/downloads.php").content
    php_release_bs = BeautifulSoup(php_release_page, "html.parser")
    releases_bs_list = php_release_bs.find_all("div", class_="content-box")
    for release_bs in releases_bs_list:
        resource_list = release_bs.find_all("li")
        for resource in resource_list:
            if ".tar.gz" in resource.text:
                version_num = resource.find("a").text.replace("php-", "").replace(".tar.gz", "")
                url = resource.find("a")["href"]
                sha256 = resource.find("span", class_="sha256").text
                if url.startswith("/"):
                    url = "https://www.php.net" + url
                version_list.append({"version": version_num, "url": url, "sha256": sha256,
                                     "file_name": url.split("/")[-1]})
    return version_list


def make_cache() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    release_list = latest_php_cache_maker() + older_php_cache_maker()
    latest_meta = []
    for version in ACCEPTED_VERSIONS:
        this_version_latest = [release for release in release_list if
                               release["version"].startswith(version)][0]["version"]
        latest_meta.append({"version_file_name": f"php{version.replace(".", "")}_ver",
                            "version": this_version_latest})

    sorted_release_list = sorted(release_list, key=lambda x: [int(c) for c in x["version"].split(".")])
    sorted_release_list.reverse()

    return release_list, latest_meta
