import httpx


def make_cache() -> list:
    url = "https://api.github.com/repos/fail2ban/fail2ban/releases/latest"
    response = httpx.get(url).json()
    version = response["tag_name"]
    package_url = f"https://github.com/fail2ban/fail2ban/archive/refs/tags/{version}.tar.gz"

    gpg = None
    for asset in response["assets"]:
        if asset["name"].endswith(".asc"):
            gpg = asset["browser_download_url"]
            break
    if not gpg:
        raise RuntimeError("No GPG signature found")
    return [{
        "version": version,
        "url": package_url,
        "gpg": gpg,
        "file_name": f"fail2ban-{version}.tar.gz"
    }]
