import httpx
from bs4 import BeautifulSoup
from base_logger import logger

BLACK_LIST_KEYWORD = ["arm", "32-bit", "test", "minimal", "ia-64", "debug"]
ACCEPTED_VERSIONS = ["5.5", "5.6", "5.7", "8.0"]


def generic_mysql_package_handler(url) -> dict:
    bs = BeautifulSoup(httpx.get(url).content, "html.parser")
    table = bs.find("table").find_all("tr")
    table = [row for row in table if len(row.find_all("td")) == 4]
    for row in table:
        td_elements = row.find_all("td")
        package_name = td_elements[0].text
        if any(key_word in package_name.lower() for key_word in BLACK_LIST_KEYWORD):
            continue
        url = td_elements[3].find("a")["href"]
        next_line = row.find_next_sibling().find_all("td")
        file_name = next_line[0].text.replace("(", "").replace(")", "")
        if ".tar.gz" not in file_name:
            continue
        md5 = next_line[1].find("code", class_="md5").text
        try:
            gpg = next_line[1].find("a", class_="signature")["href"]
        except TypeError:
            logger.info("No GPG signature found: ", file_name, ". Skipped.")
            continue
        return {
            "url": ("https://downloads.mysql.com" + url if url.startswith("/") else url),
            "file_name": file_name,
            "md5": md5,
            "gpg": ("https://downloads.mysql.com" + gpg if gpg.startswith("/") else gpg),
        }


def get_mysql_older_versions() -> list:
    release_list = []
    url = "https://downloads.mysql.com/archives/community/"
    bs = BeautifulSoup(httpx.get(url).content, "html.parser")
    available_versions = bs.find("label", string="Product Version:").parent.find_all("option")
    available_versions = [version for version in available_versions if
                          any(version.text.startswith(allowed) for allowed in ACCEPTED_VERSIONS)]
    allowed_versions = [v.text for v in available_versions if not any(c.isalpha() for c in v.text)]

    for v in allowed_versions:
        url = f"https://downloads.mysql.com/archives/community/?tpl=platform&os=2&version={v}"
        package_info = generic_mysql_package_handler(url)
        if package_info:
            package_info["version"] = v
            release_list.append(package_info)
    return release_list


def get_latest_mysql_versions():
    release_list = []
    url = "https://dev.mysql.com/downloads/mysql/"
    bs = BeautifulSoup(httpx.get(url).content, "html.parser")
    available_versions = bs.find("select", id="version").find_all("option")
    allowed_versions = [v.text.strip() for v in available_versions if not any(c.isalpha() for c in v.text)]
    for v in allowed_versions:
        url = f"https://dev.mysql.com/downloads/mysql/?tpl=platform&os=2&version={v}&osva="
        package_info = generic_mysql_package_handler(url)
        if package_info:
            package_info["version"] = v
            release_list.append(package_info)
    return release_list


def make_cache() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    release_list = get_mysql_older_versions() + get_latest_mysql_versions()
    latest_meta = [
        {"version_file_name": "mysql80_ver"},
        {"version_file_name": "mysql57_ver"},
        {"version_file_name": "mysql56_ver"},
        {"version_file_name": "mysql55_ver"},
    ]
    sorted_release_list = sorted(release_list, key=lambda x: [int(c) for c in x["version"].split(".")])
    sorted_release_list.reverse()
    mysql_55_list = [r for r in sorted_release_list if r["version"].startswith("5.5")]
    mysql_56_list = [r for r in sorted_release_list if r["version"].startswith("5.6")]
    mysql_57_list = [r for r in sorted_release_list if r["version"].startswith("5.7")]
    mysql_80_list = [r for r in sorted_release_list if r["version"].startswith("8.0")]
    latest_meta[0]["version"] = mysql_80_list[0]["version"]
    latest_meta[1]["version"] = mysql_57_list[0]["version"]
    latest_meta[2]["version"] = mysql_56_list[0]["version"]
    latest_meta[3]["version"] = mysql_55_list[0]["version"]

    return release_list, latest_meta
