import httpx


def make_cache() -> list:
    url = "https://api.github.com/repos/acmesh-official/acme.sh/releases/latest"
    response = httpx.get(url).json()
    version = response["tag_name"]
    package_url = f"https://github.com/acmesh-official/acme.sh/archive/refs/tags/{version}.tar.gz"

    return [{"file_name": "acme.sh-master.tar.gz", "version": version, "url": package_url}]
