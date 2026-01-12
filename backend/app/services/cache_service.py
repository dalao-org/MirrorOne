"""
Cache service for downloading and managing cached files.
"""
import os
import logging
import asyncio
from pathlib import Path
from typing import Callable

import httpx

logger = logging.getLogger(__name__)

# Default cache path (matches Docker volume mount)
DEFAULT_CACHE_PATH = "/app/cache"


def get_cache_path(settings: dict) -> Path:
    """Get the cache path from settings."""
    cache_path = settings.get("cache_path", DEFAULT_CACHE_PATH)
    return Path(cache_path)


def ensure_cache_dir(cache_path: Path, source: str) -> Path:
    """Ensure cache directory exists for a source."""
    source_path = cache_path / source
    source_path.mkdir(parents=True, exist_ok=True)
    return source_path


def is_file_cached(cache_path: Path, source: str, filename: str) -> bool:
    """Check if a file is already cached."""
    file_path = cache_path / source / filename
    return file_path.exists()


def get_cached_file_path(cache_path: Path, source: str, filename: str) -> Path | None:
    """Get the path to a cached file if it exists."""
    file_path = cache_path / source / filename
    if file_path.exists():
        return file_path
    return None


async def download_file(
    client: httpx.AsyncClient,
    url: str,
    dest_path: Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> bool:
    """
    Download a file to the cache.
    
    Args:
        client: HTTP client
        url: URL to download from
        dest_path: Destination file path
        progress_callback: Optional callback for progress updates (received, total)
        
    Returns:
        True if download succeeded, False otherwise
    """
    try:
        # Create parent directory if needed
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use streaming download for large files
        async with client.stream("GET", url, follow_redirects=True) as response:
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            received = 0
            
            # Write to temp file first, then rename
            temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
            
            with open(temp_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
                    received += len(chunk)
                    if progress_callback:
                        progress_callback(received, total_size)
            
            # Rename temp file to final destination
            temp_path.rename(dest_path)
            
            logger.info(f"Downloaded: {dest_path.name} ({received} bytes)")
            return True
            
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        # Clean up temp file if exists
        temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
        if temp_path.exists():
            temp_path.unlink()
        return False


async def download_resource(
    client: httpx.AsyncClient,
    url: str,
    filename: str,
    source: str,
    cache_path: Path,
    skip_existing: bool = True,
) -> bool:
    """
    Download a resource to the cache.
    
    Args:
        client: HTTP client
        url: URL to download from
        filename: Name of the file
        source: Scraper/source name
        cache_path: Base cache path
        skip_existing: Skip if file already exists
        
    Returns:
        True if file exists or download succeeded
    """
    dest_path = cache_path / source / filename
    
    # Skip if already exists
    if skip_existing and dest_path.exists():
        logger.debug(f"File already cached: {filename}")
        return True
    
    return await download_file(client, url, dest_path)


def get_cache_stats(cache_path: Path) -> dict:
    """
    Get cache statistics.
    
    Returns:
        Dict with total_files, total_size_bytes, sources
    """
    if not cache_path.exists():
        return {"total_files": 0, "total_size_bytes": 0, "sources": {}}
    
    sources = {}
    total_files = 0
    total_size = 0
    
    for source_dir in cache_path.iterdir():
        if source_dir.is_dir():
            source_files = list(source_dir.glob("*"))
            source_size = sum(f.stat().st_size for f in source_files if f.is_file())
            sources[source_dir.name] = {
                "files": len(source_files),
                "size_bytes": source_size,
            }
            total_files += len(source_files)
            total_size += source_size
    
    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "sources": sources,
    }


def find_cached_file(cache_path: Path, filename: str) -> tuple[Path, str] | None:
    """
    Find a cached file by filename across all sources.
    
    Args:
        cache_path: Base cache path
        filename: Name of the file to find
        
    Returns:
        Tuple of (file_path, source) or None if not found
    """
    logger.info(f"Looking for cached file: {filename}")
    logger.info(f"Cache path: {cache_path} (exists: {cache_path.exists()})")
    
    if not cache_path.exists():
        logger.warning(f"Cache path does not exist: {cache_path}")
        return None
    
    # List all directories in cache path for debugging
    source_dirs = [d for d in cache_path.iterdir() if d.is_dir()]
    logger.info(f"Source directories found: {[d.name for d in source_dirs]}")
    
    for source_dir in source_dirs:
        file_path = source_dir / filename
        # List first 5 files in each source dir for debugging
        files_in_dir = list(source_dir.iterdir())[:5]
        logger.info(f"Source '{source_dir.name}': {len(list(source_dir.iterdir()))} files, first 5: {[f.name for f in files_in_dir]}")
        
        if file_path.exists():
            logger.info(f"Found cached file: {file_path}")
            return (file_path, source_dir.name)
    
    logger.warning(f"File not found in cache: {filename}")
    return None


async def download_resources_parallel(
    resources: list[dict],
    cache_path: Path,
    skip_existing: bool = True,
    max_concurrent: int = 5,
    progress_callback = None,
) -> dict:
    """
    Download multiple resources in parallel.
    
    Args:
        resources: List of dicts with keys: url, file_name, source
        cache_path: Base cache path
        skip_existing: Skip if file already exists
        max_concurrent: Maximum concurrent downloads
        progress_callback: Async callback(downloaded, skipped, failed, total)
        
    Returns:
        Dict with downloaded, skipped, failed counts
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results = {"downloaded": 0, "skipped": 0, "failed": 0}
    total = len(resources)
    
    # Import broadcaster
    from app.core.log_broadcaster import broadcaster, LogLevel
    
    async def download_one(resource: dict, client: httpx.AsyncClient):
        async with semaphore:
            url = resource.get("url", "")
            filename = resource.get("file_name", "")
            source = resource.get("source", "unknown")
            
            dest_path = cache_path / source / filename
            
            # Skip if already exists
            if skip_existing and dest_path.exists():
                results["skipped"] += 1
                if progress_callback:
                    await progress_callback(results["downloaded"], results["skipped"], results["failed"], total)
                return
            
            await broadcaster.broadcast(
                f"📥 Downloading: {filename}",
                level=LogLevel.INFO,
                scraper=source,
            )
            
            success = await download_file(client, url, dest_path)
            if success:
                results["downloaded"] += 1
                file_size = dest_path.stat().st_size if dest_path.exists() else 0
                size_str = f"{file_size // 1024}KB" if file_size > 1024 else f"{file_size}B"
                await broadcaster.broadcast(
                    f"✓ Downloaded: {filename} ({size_str})",
                    level=LogLevel.SUCCESS,
                    scraper=source,
                )
            else:
                results["failed"] += 1
                await broadcaster.broadcast(
                    f"✗ Failed: {filename}",
                    level=LogLevel.ERROR,
                    scraper=source,
                )
            
            if progress_callback:
                await progress_callback(results["downloaded"], results["skipped"], results["failed"], total)
    
    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
        tasks = [download_one(resource, client) for resource in resources]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    return results


async def recache_all_resources(
    settings: dict,
    skip_existing: bool = True,
    max_concurrent: int = 5,
    progress_callback = None,
) -> dict:
    """
    Re-cache all resources currently in Redis.
    
    Args:
        settings: Settings dict
        skip_existing: Skip if file already exists (False = overwrite)
        max_concurrent: Maximum concurrent downloads
        progress_callback: Async callback for progress updates
        
    Returns:
        Dict with download statistics
    """
    from app.services import redirect_service
    
    cache_path = get_cache_path(settings)
    resources = await redirect_service.get_all_resources()
    
    if not resources:
        return {"downloaded": 0, "skipped": 0, "failed": 0, "total": 0}
    
    results = await download_resources_parallel(
        resources=resources,
        cache_path=cache_path,
        skip_existing=skip_existing,
        max_concurrent=max_concurrent,
        progress_callback=progress_callback,
    )
    
    results["total"] = len(resources)
    return results

