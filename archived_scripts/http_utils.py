import time
import httpx

HTTPX_RETRY_ATTEMPTS = 5


def httpx_get_request(url: str) -> httpx.Response | None:
    error_msg = ""
    for i in range(HTTPX_RETRY_ATTEMPTS):
        try:
            response = httpx.get(url)
            return response
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            error_msg += f"Attempt {i + 1}: {e}\n"
            time.sleep(5)
            continue
    print(f"::error title=HTTP Request Failed::Failed to make a request to {url} after {HTTPX_RETRY_ATTEMPTS} attempts.\n{error_msg}")
    raise RuntimeError(f"Failed to make a request to {url} after {HTTPX_RETRY_ATTEMPTS} attempts.")
