import httpx


def make_cache() -> list:
    release_list = []
    url = "https://api.github.com/repos/pypa/setuptools/releases"
    response = httpx.get(url).json()
    non_pre_releases = [release for release in response if not release["prerelease"]][:10]
    for release in non_pre_releases:
        version = release["tag_name"]
        package_url = f"https://github.com/pypa/setuptools/archive/refs/tags/{version}.tar.gz"
        release_list.append({
            "version": version,
            "url": package_url,
            "file_name": f"setuptools-{version}.tar.gz",
        })
    return release_list
