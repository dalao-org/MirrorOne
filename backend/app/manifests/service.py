"""Manifest build orchestration shared by startup, scheduler, and admin API."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from app import redis_client
from app.config import get_settings

from .builder import ManifestBuilder
from .metrics import set_metric
from .publisher import ManifestPublisher

logger = logging.getLogger(__name__)


def runtime_settings(database_settings: dict | None = None) -> dict:
    env = get_settings()
    values = dict(database_settings or {})
    values.setdefault("manifest_enabled", env.MANIFEST_ENABLED)
    values.setdefault("manifest_public_base_url", env.MANIFEST_PUBLIC_BASE_URL)
    values.setdefault(
        "manifest_rebuild_after_scrape",
        env.MANIFEST_REBUILD_AFTER_SCRAPE,
    )
    values.setdefault(
        "manifest_include_cache_status",
        env.MANIFEST_INCLUDE_CACHE_STATUS,
    )
    values.setdefault("manifest_keep_history", env.MANIFEST_KEEP_HISTORY)
    values.setdefault("manifest_checksum_sidecar", env.MANIFEST_CHECKSUM_SIDECAR)
    values["manifest_output_dir"] = env.MANIFEST_OUTPUT_DIR
    values["manifest_generator_commit"] = env.MANIFEST_GENERATOR_COMMIT
    values["manifest_instance_id"] = env.MANIFEST_INSTANCE_ID
    values["app_version"] = env.APP_VERSION
    return values


def get_publisher(settings: dict | None = None) -> ManifestPublisher:
    values = runtime_settings(settings)
    return ManifestPublisher(
        output_dir=Path(values["manifest_output_dir"]),
        keep_history=int(values.get("manifest_keep_history", 20)),
        sidecar=bool(values.get("manifest_checksum_sidecar", True)),
    )


async def rebuild_manifest(database_settings: dict | None = None) -> dict:
    """Build and publish a manifest, preserving the previous file on failure."""
    values = runtime_settings(database_settings)
    started = time.perf_counter()
    started_at = datetime.now(UTC)
    logger.info("manifest_build_started")
    try:
        if not values.get("manifest_enabled", True):
            status = {
                "state": "disabled",
                "last_attempt": started_at.isoformat(),
            }
            await redis_client.set_manifest_status(status)
            return status
        manifest = await ManifestBuilder(values).build()
        result = await asyncio.to_thread(
            get_publisher(values).publish,
            manifest,
        )
        duration = time.perf_counter() - started
        stats = manifest.statistics.model_dump()
        status = {
            "state": "healthy",
            "last_attempt": started_at.isoformat(),
            "last_success": result["generated_at"],
            "duration_seconds": duration,
            "revision": result["revision"],
            "sha256": result["sha256"],
            "changed": result["changed"],
            "statistics": stats,
            "checksum_coverage_percent": (
                round(stats["with_upstream_checksum"] / stats["artifact_count"] * 100, 2)
                if stats["artifact_count"]
                else 0
            ),
            "cache_coverage_percent": (
                round(stats["cached"] / stats["artifact_count"] * 100, 2)
                if stats["artifact_count"]
                else 0
            ),
            "last_error": None,
        }
        await redis_client.set_manifest_status(status)
        set_metric("mirrorone_manifest_last_success_timestamp", started_at.timestamp())
        set_metric("mirrorone_manifest_build_duration_seconds", duration)
        set_metric("mirrorone_manifest_artifact_count", stats["artifact_count"])
        set_metric(
            "mirrorone_manifest_checksum_available_count",
            stats["with_upstream_checksum"],
        )
        set_metric(
            "mirrorone_manifest_checksum_missing_count",
            stats["without_upstream_checksum"],
        )
        set_metric("mirrorone_manifest_conflict_count", stats["conflict_count"])
        set_metric(
            "mirrorone_cache_unverified_artifact_count",
            sum(
                item.mirror.cache_status == "cached" and not item.checksums
                for item in manifest.artifacts
            ),
        )
        logger.info(
            "manifest_build_succeeded revision=%s artifacts=%s conflicts=%s",
            result["revision"],
            stats["artifact_count"],
            stats["conflict_count"],
        )
        return status
    except Exception as exc:
        duration = time.perf_counter() - started
        current = await asyncio.to_thread(get_publisher(values).read_current)
        status = {
            "state": "degraded",
            "last_attempt": started_at.isoformat(),
            "last_success": current.get("generated_at") if current else None,
            "duration_seconds": duration,
            "revision": current.get("manifest_revision") if current else None,
            "last_error": f"{type(exc).__name__}: {exc}",
            "serving_last_known_good": current is not None,
        }
        try:
            await redis_client.set_manifest_status(status)
        except Exception:
            logger.exception("Unable to persist failed manifest status")
        logger.exception("manifest_build_failed")
        return status
