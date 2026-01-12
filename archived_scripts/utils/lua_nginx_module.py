import httpx


ALLOWED_NUMBER_OF_VERSIONS = 5


def make_cache() -> list:
    release_list = []
    url = "https://api.github.com/repos/openresty/lua-nginx-module/git/refs/tags"
    response = httpx.get(url).json()
    tags = [tag["ref"].replace("refs/tags/", "") for tag in response if "rc" not in tag["ref"]]
    tags.reverse()
    tags = tags[:ALLOWED_NUMBER_OF_VERSIONS]
    for tag in tags:
        release_list.append({
            "version": tag,
            "url": f"https://github.com/openresty/lua-nginx-module/archive/refs/tags/{tag}.zip",
            "file_name": f"lua-nginx-module-{tag}.zip"
        })
    return release_list
