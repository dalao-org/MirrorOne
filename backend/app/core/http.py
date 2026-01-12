"""
HTTP utilities for making requests with retry logic.
"""
import asyncio
from typing import Any
import httpx
from app.config import get_settings

settings = get_settings()

DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_DELAY = 2.0


async def http_get(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = MAX_RETRIES,
) -> httpx.Response:
    """
    Make an async HTTP GET request with retry logic.
    
    Args:
        url: URL to request
        headers: Optional headers
        timeout: Request timeout in seconds
        retries: Number of retries on failure
        
    Returns:
        httpx.Response object
        
    Raises:
        httpx.HTTPError: If all retries fail
    """
    last_exception: Exception | None = None
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(retries):
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
                last_exception = e
                if attempt < retries - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                continue
            except httpx.HTTPStatusError as e:
                # Don't retry on 4xx errors
                if 400 <= e.response.status_code < 500:
                    raise
                last_exception = e
                if attempt < retries - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                continue
    
    raise last_exception or Exception(f"Failed to fetch {url} after {retries} attempts")


async def http_get_json(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = MAX_RETRIES,
) -> Any:
    """
    Make an async HTTP GET request and return JSON response.
    
    Args:
        url: URL to request
        headers: Optional headers
        timeout: Request timeout in seconds
        retries: Number of retries on failure
        
    Returns:
        Parsed JSON response
    """
    response = await http_get(url, headers, timeout, retries)
    return response.json()
