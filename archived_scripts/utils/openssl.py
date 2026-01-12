import httpx


def make_cache() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    release_list = []
    latest_meta = [{"version_file_name": "openssl3_ver"}, {"version_file_name": "openssl11_ver"}]

    url = "https://api.github.com/repos/openssl/openssl/releases"
    non_pre_release = [r for r in httpx.get(url).json() if not r["prerelease"]]
    for release in non_pre_release:
        version_name = release["name"].lower().replace("openssl ", "")
        for asset in release["assets"]:
            if asset["name"].endswith(".tar.gz"):
                release_list.append({
                    "version": version_name,
                    "url": asset["browser_download_url"],
                    "sha256": asset["browser_download_url"]+".sha256",
                    "sha1": asset["browser_download_url"] + ".sha1",
                    "pgp": asset["browser_download_url"]+".asc",
                    "file_name": asset["name"]
                })
                break
    version11_list = [r for r in release_list if r["version"].startswith("1.1")]
    version3_list = [r for r in release_list if r["version"].startswith("3.")]
    latest_meta[0]["version"] = version3_list[0]["version"]
    latest_meta[1]["version"] = version11_list[0]["version"]
    return release_list, latest_meta
