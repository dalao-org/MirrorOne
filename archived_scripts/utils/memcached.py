import httpx

ALLOWED_NUMBER_OF_VERSIONS = 5


def make_cache() -> list:
    release_list = []
    url = "https://api.github.com/repos/memcached/memcached/git/refs/tags"
    response = httpx.get(url).json()
    tags = [tag["ref"].replace("refs/tags/", "") for tag in response]
    tags.reverse()
    tags = tags[:ALLOWED_NUMBER_OF_VERSIONS]
    for tag in tags:
        release_list.append({
            "version": tag,
            "url": f"http://www.memcached.org/files/memcached-{tag}.tar.gz",
            "file_name": f"memcached-{tag}.tar.gz"
        })
    return release_list
