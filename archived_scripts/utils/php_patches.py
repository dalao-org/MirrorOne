import httpx


def make_cache() -> list:
    url_dict = {
        "fpm-race-condition.patch": "https://bugs.php.net/patch-display.php?bug_id=65398&patch=fpm-race-condition.patch&revision=1375772074&download=1"
    }

    for k, v in url_dict.items():
        r = httpx.get(v)
        with open(f"./output/src/{k}", 'wb') as f:
            f.write(r.content)

    return [{"file_name": k, "url": f"/src/{k}"} for k, v in url_dict.items()]
