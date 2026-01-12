"""
Redirect router for public file redirects.
"""
import json
from datetime import datetime, UTC
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse, PlainTextResponse, JSONResponse, FileResponse

from app.services import redirect_service
from app.services import cache_service
from app import redis_client
from app.database import get_db_session
from app.services import setting_service

router = APIRouter(tags=["Redirect"])


async def get_mirror_settings() -> dict:
    """Get mirror_type and cache_path from settings."""
    async with get_db_session() as db:
        settings = await setting_service.get_all_settings(db)
        return settings


@router.get("/src/{filename:path}")
async def redirect_file(filename: str, force_redirect: bool = False):
    """
    Redirect to the actual file download URL or serve from cache.
    
    Behavior depends on mirror_type setting:
    - "redirect": 301 redirect to original URL
    - "cache": Serve file from local cache
    
    Query parameters:
    - force_redirect: If True, always redirect to original URL (bypass cache mode)
    """
    settings = await get_mirror_settings()
    mirror_type = settings.get("mirror_type", "redirect")
    
    # Check if file exists in rules
    url = await redirect_service.get_redirect_url(filename)
    
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found in redirect rules",
        )
    
    # Force redirect mode if requested
    if force_redirect:
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    
    # Cache mode: serve from local cache
    if mirror_type == "cache":
        cache_path = cache_service.get_cache_path(settings)
        cached = cache_service.find_cached_file(cache_path, filename)
        
        if cached:
            file_path, source = cached
            return FileResponse(
                path=str(file_path),
                filename=filename,
                media_type="application/octet-stream",
            )
        else:
            # File not yet cached, fall back to redirect
            return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    
    # Redirect mode (default)
    return RedirectResponse(url=url, status_code=status.HTTP_301_MOVED_PERMANENTLY)


@router.get("/oneinstack/src/{filename:path}")
async def redirect_file_legacy(filename: str, force_redirect: bool = False):
    """
    Legacy redirect path for compatibility.
    
    Redirects /oneinstack/src/file.tar.gz to the actual URL.
    """
    # Use the same logic as redirect_file
    return await redirect_file(filename, force_redirect)


@router.get("/suggest_versions.txt", response_class=PlainTextResponse)
async def get_suggest_versions():
    """
    Get suggested versions file.
    
    Returns a plain text file with version suggestions for OneinStack.
    Format: key=version per line.
    """
    content = await redirect_service.get_suggest_versions_content()
    return PlainTextResponse(content=content)


@router.get("/_redirects", response_class=PlainTextResponse)
async def get_redirects_file():
    """
    Generate Netlify-style _redirects file.
    
    Format: /src/filename.tar.gz https://target-url.com/file.tar.gz 301
    """
    resources = await redirect_service.get_all_resources()
    lines = []
    for res in resources:
        filename = res.get("file_name", "")
        url = res.get("url", "")
        if filename and url:
            lines.append(f"/src/{filename} {url} 301")
    return PlainTextResponse(content="\n".join(lines))


@router.get("/latest_meta.json")
async def get_latest_meta():
    """
    Get latest version metadata as JSON.
    
    Returns all version metadata from scrapers.
    """
    versions = await redis_client.get_all_version_metas()
    scheduler_times = await redis_client.get_scheduler_times()
    
    return JSONResponse(content={
        "generated_at": datetime.now(UTC).isoformat(),
        "last_scrape": scheduler_times.get("last_run"),
        "versions": versions,
    })


@router.get("/resource.json")
async def get_resources_json():
    """
    Get all resources as JSON.
    
    Returns complete resource list with URLs and metadata.
    """
    resources = await redirect_service.get_all_resources()
    
    # Group by source
    by_source = {}
    for res in resources:
        source = res.get("source", "unknown")
        if source not in by_source:
            by_source[source] = []
        by_source[source].append({
            "file": res.get("file_name"),
            "url": res.get("url"),
            "version": res.get("version"),
        })
    
    return JSONResponse(content={
        "generated_at": datetime.now(UTC).isoformat(),
        "total": len(resources),
        "sources": by_source,
    })

