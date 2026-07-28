"""
Cache service for downloading and managing cached files.
"""
import logging
import asyncio
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from app.manifests.checksum import choose_strongest, digest_file, digests_equal
from app.manifests.metrics import increment_metric
from app.manifests.validator import (
    ensure_within_root,
    validate_filename,
    validate_network_target,
)

logger = logging.getLogger(__name__)

# Default cache path (matches Docker volume mount)
DEFAULT_CACHE_PATH = "/app/cache"


class CacheIntegrityError(RuntimeError):
    """A downloaded or existing file does not match upstream metadata."""


def _redact_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _cache_file_path(cache_path: Path, source: str, filename: str) -> Path:
    filename = validate_filename(filename)
    if (
        not source
        or source in {".", ".."}
        or "/" in source
        or "\\" in source
        or "\x00" in source
    ):
        raise ValueError("source must be a safe directory name")
    return ensure_within_root(cache_path / source / filename, cache_path)


def _metadata_path(dest_path: Path) -> Path:
    return dest_path.parent / ".metadata" / f"{dest_path.name}.json"


def _write_cache_metadata(dest_path: Path, metadata: dict) -> None:
    path = _metadata_path(dest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    content = json.dumps(metadata, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    with temporary.open("wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _read_cache_metadata(dest_path: Path) -> dict:
    try:
        return json.loads(_metadata_path(dest_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _quarantine(path: Path, reason: str) -> Path:
    cache_root = path.parent.parent
    quarantine_dir = cache_root / "quarantine" / path.parent.name
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = quarantine_dir / f"{path.name}.{timestamp}.{reason}"
    if destination.exists():
        destination = quarantine_dir / f"{destination.name}.{uuid.uuid4().hex[:8]}"
    os.replace(path, destination)
    return destination


def _verify_existing_file(
    dest_path: Path,
    checksums: dict[str, str],
) -> tuple[bool, dict]:
    """Re-check an existing cache entry using upstream or prior observed metadata."""
    if not dest_path.is_file() or dest_path.stat().st_size <= 0:
        if dest_path.exists():
            quarantined = _quarantine(dest_path, "empty_file")
            return False, {
                "event": "cache_empty_file",
                "quarantined_path": str(quarantined),
            }
        return False, {"event": "cache_file_missing"}

    metadata = _read_cache_metadata(dest_path)
    selected = choose_strongest(checksums)
    if selected:
        algorithm, expected = selected
        actual = digest_file(dest_path, algorithm)
        if not digests_equal(actual, expected):
            quarantined = _quarantine(dest_path, "checksum_mismatch")
            increment_metric("mirrorone_cache_checksum_mismatch_total")
            return False, {
                "event": "cache_checksum_mismatch",
                "algorithm": algorithm,
                "expected": expected,
                "actual": actual,
                "quarantined_path": str(quarantined),
            }
        integrity_status = "verified_upstream_checksum"
    else:
        integrity_status = "unverified_upstream_checksum_unavailable"

    observed_sha256 = digest_file(dest_path, "sha256")
    previous_observed = metadata.get("observed_digests", {}).get("sha256")
    if (
        not selected
        and previous_observed
        and not digests_equal(observed_sha256, previous_observed)
    ):
        quarantined = _quarantine(dest_path, "observed_digest_changed")
        return False, {
            "event": "cache_observed_digest_changed",
            "algorithm": "sha256",
            "expected": previous_observed,
            "actual": observed_sha256,
            "quarantined_path": str(quarantined),
        }

    _write_cache_metadata(dest_path, {
        "cached_at": metadata.get("cached_at")
        or datetime.fromtimestamp(dest_path.stat().st_mtime, UTC).isoformat(),
        "integrity_status": integrity_status,
        "observed_digests": {"sha256": observed_sha256},
        "upstream_checksums": checksums,
        "last_verified_at": datetime.now(UTC).isoformat(),
    })
    return True, {"event": "cache_integrity_verified"}


async def _record_cache_failure(filename: str, details: dict) -> None:
    logger.error(
        "%s filename=%s algorithm=%s expected=%s actual=%s quarantined=%s",
        details.get("event"),
        filename,
        details.get("algorithm"),
        details.get("expected"),
        details.get("actual"),
        details.get("quarantined_path"),
    )
    try:
        from app import redis_client
        await redis_client.record_manifest_event(
            details.get("event", "cache_integrity_failed"),
            filename=filename,
            **{
                key: value
                for key, value in details.items()
                if key != "event"
            },
        )
    except Exception:
        logger.exception("Unable to persist cache integrity event")


def get_cache_info(cache_path: Path, source: str, filename: str) -> dict | None:
    """Return safe cache state and private observed metadata for one resource."""
    try:
        file_path = _cache_file_path(cache_path, source, filename)
    except ValueError:
        return None
    if not file_path.is_file() or file_path.stat().st_size <= 0:
        return None
    metadata = _read_cache_metadata(file_path)
    stat = file_path.stat()
    return {
        "available": True,
        "path": file_path,
        "size_bytes": stat.st_size,
        "cached_at": metadata.get("cached_at")
        or datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
        "integrity_status": metadata.get("integrity_status"),
        "observed_digests": metadata.get("observed_digests", {}),
    }


def get_cache_path(settings: dict) -> Path:
    """Get the cache path from settings."""
    cache_path = settings.get("cache_path", DEFAULT_CACHE_PATH)
    return Path(cache_path)


def ensure_cache_dir(cache_path: Path, source: str) -> Path:
    """Ensure cache directory exists for a source."""
    source_path = _cache_file_path(cache_path, source, "_placeholder").parent
    source_path.mkdir(parents=True, exist_ok=True)
    return source_path


def is_file_cached(cache_path: Path, source: str, filename: str) -> bool:
    """Check if a file is already cached."""
    return get_cache_info(cache_path, source, filename) is not None


def get_cached_file_path(cache_path: Path, source: str, filename: str) -> Path | None:
    """Get the path to a cached file if it exists."""
    file_path = _cache_file_path(cache_path, source, filename)
    if file_path.is_file() and file_path.stat().st_size > 0:
        return file_path
    return None


async def download_file(
    client: httpx.AsyncClient,
    url: str,
    dest_path: Path,
    progress_callback: Callable[[int, int], None] | None = None,
    checksums: dict[str, str] | None = None,
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
    temp_path = dest_path.with_name(f"{dest_path.name}.{uuid.uuid4().hex}.part")
    response: httpx.Response | None = None
    try:
        # Create parent directory if needed
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        current_url = url
        for redirect_count in range(11):
            await validate_network_target(current_url)
            request = client.build_request("GET", current_url)
            response = await client.send(
                request,
                stream=True,
                follow_redirects=False,
            )
            if response.is_redirect and response.headers.get("location"):
                if redirect_count >= 10:
                    raise httpx.TooManyRedirects(
                        "Maximum of 10 redirects exceeded",
                        request=request,
                    )
                next_url = urljoin(str(response.url), response.headers["location"])
                await response.aclose()
                response = None
                current_url = next_url
                continue
            break
        if response is None:
            raise RuntimeError("download did not produce a response")
        try:
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            received = 0
            
            with open(temp_path, "wb") as f:
                async for chunk in response.aiter_raw(chunk_size=8192):
                    f.write(chunk)
                    received += len(chunk)
                    if progress_callback:
                        progress_callback(received, total_size)
                f.flush()
                os.fsync(f.fileno())

            if received <= 0:
                raise CacheIntegrityError("downloaded file is empty")
            if total_size and received != total_size:
                raise CacheIntegrityError(
                    f"download size mismatch: expected={total_size} actual={received}"
                )

            selected = choose_strongest(checksums or {})
            if selected:
                algorithm, expected = selected
                actual = digest_file(temp_path, algorithm)
                if not digests_equal(actual, expected):
                    quarantined = _quarantine(temp_path, "checksum_mismatch")
                    increment_metric("mirrorone_cache_checksum_mismatch_total")
                    try:
                        from app import redis_client
                        await redis_client.record_manifest_event(
                            "cache_checksum_mismatch",
                            filename=dest_path.name,
                            algorithm=algorithm,
                            expected=expected,
                            actual=actual,
                            quarantined_path=str(quarantined),
                        )
                    except Exception:
                        logger.exception("Unable to persist cache_checksum_mismatch event")
                    raise CacheIntegrityError(
                        f"checksum mismatch for {dest_path.name}: "
                        f"algorithm={algorithm} expected={expected} actual={actual}"
                    )
                integrity_status = "verified_upstream_checksum"
            else:
                integrity_status = "unverified_upstream_checksum_unavailable"
                logger.warning(
                    "cache_promoted_without_upstream_checksum filename=%s",
                    dest_path.name,
                )

            observed_sha256 = digest_file(temp_path, "sha256")
            os.replace(temp_path, dest_path)
            cached_at = datetime.now(UTC).isoformat()
            _write_cache_metadata(dest_path, {
                "cached_at": cached_at,
                "integrity_status": integrity_status,
                "observed_digests": {"sha256": observed_sha256},
                "upstream_checksums": checksums or {},
            })
            logger.info(f"Downloaded: {dest_path.name} ({received} bytes)")
            return True
        finally:
            await response.aclose()
            response = None
            
    except Exception as e:
        logger.error("Failed to download %s: %s", _redact_url(url), e)
        # Clean up temp file if exists
        if temp_path.exists():
            temp_path.unlink()
        return False
    finally:
        if response is not None:
            await response.aclose()


async def download_resource(
    client: httpx.AsyncClient,
    url: str,
    filename: str,
    source: str,
    cache_path: Path,
    skip_existing: bool = True,
    checksums: dict[str, str] | None = None,
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
    dest_path = _cache_file_path(cache_path, source, filename)
    
    # Skip if already exists
    if skip_existing and dest_path.is_file():
        valid, details = _verify_existing_file(dest_path, checksums or {})
        if not valid:
            await _record_cache_failure(filename, details)
            return False
        logger.debug(f"File already cached: {filename}")
        return True
    
    return await download_file(client, url, dest_path, checksums=checksums)


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
        if source_dir.is_dir() and source_dir.name != "quarantine":
            source_files = [path for path in source_dir.glob("*") if path.is_file()]
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
    try:
        validate_filename(filename)
    except ValueError:
        logger.warning("Rejected unsafe cache filename")
        return None
    
    if not cache_path.exists():
        logger.warning(f"Cache path does not exist: {cache_path}")
        return None
    
    source_dirs = [
        directory
        for directory in cache_path.iterdir()
        if directory.is_dir()
        and directory.name != "quarantine"
        and not directory.name.startswith(".")
    ]
    
    for source_dir in source_dirs:
        file_path = ensure_within_root(source_dir / filename, cache_path)
        
        if file_path.is_file() and file_path.stat().st_size > 0:
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
            checksums = dict(resource.get("checksums") or {})
            if resource.get("checksum") and resource.get("checksum_type"):
                checksums[resource["checksum_type"]] = resource["checksum"]
            try:
                dest_path = _cache_file_path(cache_path, source, filename)
            except ValueError as exc:
                results["failed"] += 1
                logger.error("Rejected unsafe cache resource: %s", exc)
                return
            
            # Skip if already exists
            if skip_existing and dest_path.is_file():
                valid, details = _verify_existing_file(dest_path, checksums)
                if not valid:
                    results["failed"] += 1
                    await _record_cache_failure(filename, details)
                    return
                results["skipped"] += 1
                if progress_callback:
                    await progress_callback(results["downloaded"], results["skipped"], results["failed"], total)
                return
            
            await broadcaster.broadcast(
                f"📥 Downloading: {filename}",
                level=LogLevel.INFO,
                scraper=source,
            )
            
            success = await download_file(
                client,
                url,
                dest_path,
                checksums=checksums,
            )
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
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in task_results:
            if isinstance(result, Exception):
                results["failed"] += 1
                logger.error(
                    "Unexpected parallel cache failure",
                    exc_info=(type(result), result, result.__traceback__),
                )
    
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

