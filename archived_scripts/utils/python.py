import httpx
from bs4 import BeautifulSoup

# Python 2.7 and supported 3.x
ALLOWED_VERSIONS = ["2.7", "3.8", "3.9", "3.10", "3.11", "3.12"]


def make_cache() -> list:
    release_list = []
    url = "https://www.python.org/ftp/python/"
    response = httpx.get(url)
    soup = BeautifulSoup(response.text, "html.parser").find("pre")
    version_soups = soup.find_all("a")
    version_num_list = []
    final_version_list = []
    for v in version_soups:
        # List all versions under ALLOWED_VERSIONS
        if any(minor for minor in ALLOWED_VERSIONS if v.text.startswith(minor)):
            version_text = v.text.replace("/", "")
            version_num_list.append(version_text)

    for minor in ALLOWED_VERSIONS:
        # Get latest 3 revisions of each minor version
        this_minor_version_list = [v for v in version_num_list if v.startswith(minor)]
        latest_of_minor = []
        for version in this_minor_version_list:
            try:
                revision = version.split(".")[2]
            except IndexError:
                # Version like `2.7`
                # In Python 3, first version will not be affected as they are tagged as `3.x.0`
                this_minor_version_list.remove(version)
                version_num_list.remove(version)
                continue
            latest_of_minor.append(int(revision))
        latest_of_minor = sorted(latest_of_minor, reverse=True)[:3]

        for version in version_num_list:
            if version.startswith(minor):
                if int(version.split(".")[2]) in latest_of_minor:
                    final_version_list.append({
                        "version": version,
                        "url": f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz",
                        "file_name": f"Python-{version}.tgz",
                        "pgp": f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz.asc",
                    })
    return final_version_list
