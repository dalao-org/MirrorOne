"""Public and authenticated artifact manifest endpoints."""
from __future__ import annotations

import asyncio
import hashlib
import json
from email.utils import formatdate, parsedate_to_datetime
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from app import redis_client
from app.core.dependencies import CurrentUser
from app.database import get_db_session
from app.manifests.metrics import render_metrics
from app.manifests.service import get_publisher, rebuild_manifest
from app.services import setting_service

router = APIRouter(tags=["Manifests"])
SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "manifests"
    / "schema"
    / "artifacts-v1.schema.json"
)


@lru_cache(maxsize=256)
def _cached_file_headers(
    path_value: str,
    modified_ns: int,
    size: int,
    schema_version: bool,
) -> dict[str, str]:
    path = Path(path_value)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    headers = {
        "Cache-Control": "public, max-age=300, stale-if-error=86400",
        "ETag": f'"{digest}"',
        "Last-Modified": formatdate(modified_ns / 1_000_000_000, usegmt=True),
    }
    if schema_version:
        document = json.loads(path.read_text(encoding="utf-8"))
        headers["X-MirrorOne-Schema-Version"] = "1"
        headers["X-MirrorOne-Manifest-Revision"] = document["manifest_revision"]
    return headers


def _file_headers(path: Path, schema_version: bool = False) -> dict[str, str]:
    stat = path.stat()
    return dict(_cached_file_headers(
        str(path),
        stat.st_mtime_ns,
        stat.st_size,
        schema_version,
    ))


def _not_modified(request: Request, path: Path, headers: dict[str, str]) -> bool:
    if_none_match = request.headers.get("if-none-match")
    if if_none_match:
        candidates = {token.strip() for token in if_none_match.split(",")}
        return "*" in candidates or headers["ETag"] in candidates
    if_modified_since = request.headers.get("if-modified-since")
    if if_modified_since:
        try:
            requested_time = parsedate_to_datetime(if_modified_since).timestamp()
            resource_time = parsedate_to_datetime(
                headers["Last-Modified"]
            ).timestamp()
            return int(resource_time) <= int(requested_time)
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
    return False


async def _serve_file(
    request: Request,
    path: Path,
    media_type: str,
    *,
    schema_version: bool = False,
) -> Response:
    if not await asyncio.to_thread(path.is_file):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No valid manifest snapshot is available yet",
        )
    headers = await asyncio.to_thread(
        _file_headers,
        path,
        schema_version,
    )
    if _not_modified(request, path, headers):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return FileResponse(path, media_type=media_type, headers=headers)


@router.get("/manifests/artifacts.json")
async def get_artifacts_manifest(request: Request):
    publisher = get_publisher()
    return await _serve_file(
        request,
        publisher.manifest_path,
        "application/json; charset=utf-8",
        schema_version=True,
    )


@router.get("/manifests/artifacts.json.sha256")
async def get_artifacts_manifest_checksum(request: Request):
    publisher = get_publisher()
    if not publisher.sidecar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest checksum sidecar is disabled",
        )
    return await _serve_file(
        request,
        publisher.sidecar_path,
        "text/plain; charset=utf-8",
    )


@router.get("/manifests/schema/artifacts-v1.schema.json")
async def get_artifacts_schema(request: Request):
    return await _serve_file(request, SCHEMA_PATH, "application/schema+json")


@router.get("/api/manifests/status")
async def get_manifest_status(current_user: CurrentUser):
    manifest_status = await redis_client.get_manifest_status()
    manifest_status["recent_events"] = await redis_client.get_manifest_events()
    return manifest_status


@router.post("/api/manifests/rebuild")
async def rebuild_artifacts_manifest(current_user: CurrentUser):
    async with get_db_session() as db:
        settings = await setting_service.get_all_settings(db)
    result = await rebuild_manifest(settings)
    code = (
        status.HTTP_200_OK
        if result.get("state") in {"healthy", "disabled"}
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(content=result, status_code=code)


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return PlainTextResponse(
        render_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
