import httpx
import re


def make_cache() -> list:
    release_list = []
    url = "https://raw.githubusercontent.com/redis/redis-hashes/master/README"
    response = httpx.get(url).text
    lines = response.split("\n")
    for line in lines:
        match = re.search(r"(?:hash )(?P<v>redis-\d+\.\d+\.\d+)(?:\.tar\.gz sha256 )"
                          r"(?P<sha256>[\w]{64}) (?P<url>http[s]?:\/\/[\w|\.\/|\-]+)$", line)
        if match:
            version = match.group("v")
            sha256 = match.group("sha256")
            url = match.group("url")
            if "https" not in url and "http" in url:
                url = url.replace("http", "https")
            release_list.append({
                "version": version,
                "sha256": sha256,
                "url": url,
                "file_name": url.split("/")[-1]
            })
    return release_list
