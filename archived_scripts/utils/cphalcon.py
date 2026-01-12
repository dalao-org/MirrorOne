import httpx


def make_cache() -> list:
    resource_list = []

    url = "https://api.github.com/repos/phalcon/cphalcon/releases"
    full_release_list = httpx.get(url).json()
    non_pre_release_list = [release for release in full_release_list if not release["prerelease"]]
    tag_list = [release["tag_name"] for release in non_pre_release_list]
    for tag in tag_list:
        tag_tar_gz = f"https://github.com/phalcon/cphalcon/archive/refs/tags/{tag}.tar.gz"
        resource_list.append({
            "url": tag_tar_gz,
            "file_name": f"cphalcon-{tag}.tar.gz"
        })
    return resource_list
