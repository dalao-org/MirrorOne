"""
Redis client for redirect rules and version metadata storage.
"""
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis

from app.config import get_settings
from app.manifests.checksum import (
    choose_strongest,
    normalize_algorithm,
    validate_checksum,
)
from app.manifests.validator import validate_filename, validate_source_url

settings = get_settings()
logger = logging.getLogger(__name__)

# Redis connection pool
_redis_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get Redis connection from pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def close_redis():
    """Close Redis connection pool."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


# Redis key constants
REDIRECT_RULES_KEY = "redirect:rules"
VERSION_META_KEY = "meta:versions"
SCHEDULER_LAST_RUN_KEY = "scheduler:last_run"
SCHEDULER_NEXT_RUN_KEY = "scheduler:next_run"
REDIRECT_ALIASES_KEY = "redirect:aliases"
REDIRECT_CONFLICTS_KEY = "redirect:conflicts"
REDIS_SCHEMA_VERSION_KEY = "meta:redis_schema_version"
MANIFEST_STATUS_KEY = "manifest:status"
MANIFEST_EVENTS_KEY = "manifest:events"
MANIFEST_METADATA_UPDATE_KEY = "manifest:metadata_update"
MANIFEST_METADATA_UPDATE_TTL_SECONDS = 900
REDIS_SCHEMA_VERSION = 2


async def get_redirect_url(filename: str) -> dict[str, Any] | None:
    """
    Get redirect URL for a filename.
    
    Args:
        filename: The filename to look up (e.g., "nginx-1.27.0.tar.gz")
        
    Returns:
        Dict with url, version, source, updated_at or None if not found
    """
    r = await get_redis()
    data = await r.hget(REDIRECT_RULES_KEY, filename)
    canonical_filename = None
    if not data:
        alias_data = await r.hget(REDIRECT_ALIASES_KEY, filename)
        if alias_data:
            alias = json.loads(alias_data)
            canonical_filename = alias.get("canonical_filename", "")
            data = await r.hget(
                REDIRECT_RULES_KEY,
                canonical_filename,
            )
    if data:
        rule = json.loads(data)
        if canonical_filename:
            rule["_canonical_filename"] = canonical_filename
        return rule
    return None


async def record_manifest_event(event: str, **details: Any) -> None:
    """Append a bounded structured anomaly/audit event."""
    r = await get_redis()
    payload = {
        "event": event,
        "timestamp": datetime.now(UTC).isoformat(),
        **details,
    }
    await r.lpush(MANIFEST_EVENTS_KEY, json.dumps(payload, sort_keys=True))
    await r.ltrim(MANIFEST_EVENTS_KEY, 0, 199)


async def set_redirect_rule(
    *,
    filename: str,
    url: str,
    version: str,
    source: str,
    checksum: str | None = None,
    checksum_type: str | None = None,
    checksums: dict[str, str] | None = None,
    kind: str = "source",
    platform: dict | None = None,
    channel: str | None = None,
    aliases: list[str] | None = None,
    checksum_source_url: str | None = None,
    checksum_unavailable_reason: str | None = None,
    component: str | None = None,
) -> bool:
    """
    Set a redirect rule.
    
    Args:
        filename: The filename key
        url: The redirect target URL
        version: Version string
        source: Source scraper name
    """
    filename = validate_filename(filename)
    url = validate_source_url(url)
    aliases = sorted({
        validate_filename(alias)
        for alias in (aliases or [])
        if alias and alias != filename
    })
    normalized_checksums: dict[str, str] = {}
    for raw_algorithm, raw_digest in (checksums or {}).items():
        algorithm = normalize_algorithm(raw_algorithm)
        if algorithm and validate_checksum(algorithm, raw_digest):
            normalized_checksums[algorithm] = raw_digest.strip().lower()
    scalar_algorithm = normalize_algorithm(checksum_type)
    if (
        checksum
        and scalar_algorithm
        and validate_checksum(scalar_algorithm, checksum)
    ):
        normalized_checksums[scalar_algorithm] = checksum.strip().lower()
    selected_checksum = choose_strongest(normalized_checksums)

    now = datetime.now(UTC).isoformat()
    rule = {
        "url": url,
        "version": version.strip(),
        "source": source,
        "checksum": selected_checksum[1] if selected_checksum else None,
        "checksum_type": selected_checksum[0] if selected_checksum else None,
        "checksums": normalized_checksums,
        "kind": kind,
        "platform": platform or {"os": "any", "arch": "any", "libc": None},
        "channel": channel or "unknown",
        "aliases": aliases,
        "checksum_source_url": checksum_source_url,
        "checksum_unavailable_reason": (
            checksum_unavailable_reason
            if not normalized_checksums
            else None
        ),
        "component": component,
        "updated_at": now,
    }
    r = await get_redis()
    filename_alias_raw = await r.hget(REDIRECT_ALIASES_KEY, filename)
    if filename_alias_raw:
        alias_owner = json.loads(filename_alias_raw).get("canonical_filename")
        if alias_owner and alias_owner != filename:
            conflict = {
                "filename": filename,
                "reason": "alias_conflict",
                "candidates": [
                    {"canonical_filename": alias_owner},
                    {"canonical_filename": filename, "source": source, "url": url},
                ],
                "updated_at": now,
            }
            await r.hset(
                REDIRECT_CONFLICTS_KEY,
                filename,
                json.dumps(conflict, sort_keys=True),
            )
            await record_manifest_event(
                "manifest_conflict_detected",
                filename=filename,
                reason="alias_conflict",
            )
            return False
    current_raw = await r.hget(REDIRECT_RULES_KEY, filename)
    current = json.loads(current_raw) if current_raw else None
    existing_conflict_raw = await r.hget(REDIRECT_CONFLICTS_KEY, filename)
    if existing_conflict_raw:
        existing_conflict = json.loads(existing_conflict_raw)
        candidate_map = {
            (item.get("source"), item.get("url")): item
            for item in existing_conflict.get("candidates", [])
            if item.get("source") != source
        }
        candidate_map[(source, url)] = rule
        candidates = list(candidate_map.values())
        if len({item.get("url") for item in candidates}) > 1:
            existing_conflict["candidates"] = candidates
            existing_conflict["updated_at"] = now
            await r.hset(
                REDIRECT_CONFLICTS_KEY,
                filename,
                json.dumps(existing_conflict, sort_keys=True),
            )
            return False
        await r.hdel(REDIRECT_CONFLICTS_KEY, filename)

    if current and current.get("url") != url:
        candidates = [current, rule]
        unique = {
            (item.get("source"), item.get("url")): item
            for item in candidates
        }
        conflict = {
            "filename": filename,
            "reason": "same_filename_different_source_url",
            "candidates": list(unique.values()),
            "updated_at": now,
        }
        await r.hset(
            REDIRECT_CONFLICTS_KEY,
            filename,
            json.dumps(conflict, sort_keys=True),
        )
        await record_manifest_event(
            "manifest_conflict_detected",
            filename=filename,
            reason=conflict["reason"],
        )
        logger.warning(
            "manifest_conflict_detected filename=%s reason=%s",
            filename,
            conflict["reason"],
        )
        return False

    if current:
        old_checksums = current.get("checksums") or {}
        if old_checksums and not normalized_checksums:
            rule["checksums"] = old_checksums
            rule["checksum_type"] = current.get("checksum_type")
            rule["checksum"] = current.get("checksum")
            rule["checksum_source_url"] = current.get("checksum_source_url")
            rule["checksum_unavailable_reason"] = None
        rule["aliases"] = sorted(set(current.get("aliases") or []) | set(aliases))
        if rule["kind"] == "source" and current.get("kind") not in {None, "source"}:
            rule["kind"] = current["kind"]
        current_platform = current.get("platform") or {}
        if (
            rule["platform"].get("os") == "any"
            and rule["platform"].get("arch") == "any"
            and (
                current_platform.get("os") not in {None, "any"}
                or current_platform.get("arch") not in {None, "any"}
            )
        ):
            rule["platform"] = current_platform
        if rule["channel"] == "unknown" and current.get("channel") not in {None, "unknown"}:
            rule["channel"] = current["channel"]
        if not rule.get("component") and current.get("component"):
            rule["component"] = current["component"]
        if (
            old_checksums
            and normalized_checksums
            and old_checksums != normalized_checksums
        ):
            rule["checksums"] = old_checksums
            rule["checksum_type"] = current.get("checksum_type")
            rule["checksum"] = current.get("checksum")
            rule["pending_checksums"] = normalized_checksums
            await record_manifest_event(
                "upstream_checksum_changed",
                filename=filename,
                source=source,
                previous=old_checksums,
                observed=normalized_checksums,
            )
            logger.warning("upstream_checksum_changed filename=%s source=%s", filename, source)
        comparable_current = {
            key: value
            for key, value in current.items()
            if key != "updated_at"
        }
        comparable_rule = {
            key: value
            for key, value in rule.items()
            if key != "updated_at"
        }
        if comparable_current == comparable_rule:
            rule["updated_at"] = current.get("updated_at", now)

    await r.hset(REDIRECT_RULES_KEY, filename, json.dumps(rule, sort_keys=True))
    for alias in rule["aliases"]:
        canonical_raw = await r.hget(REDIRECT_RULES_KEY, alias)
        alias_raw = await r.hget(REDIRECT_ALIASES_KEY, alias)
        alias_owner = json.loads(alias_raw).get("canonical_filename") if alias_raw else None
        if canonical_raw or (alias_owner and alias_owner != filename):
            conflict = {
                "filename": alias,
                "reason": "alias_conflict",
                "candidates": [
                    {"canonical_filename": filename, "source": source, "url": url},
                    {"canonical_filename": alias_owner or alias},
                ],
                "updated_at": now,
            }
            await r.hset(
                REDIRECT_CONFLICTS_KEY,
                alias,
                json.dumps(conflict, sort_keys=True),
            )
            await record_manifest_event(
                "manifest_conflict_detected",
                filename=alias,
                reason="alias_conflict",
            )
            continue
        await r.hset(
            REDIRECT_ALIASES_KEY,
            alias,
            json.dumps(
                {"canonical_filename": filename, "source": source, "updated_at": now},
                sort_keys=True,
            ),
        )
    return True


async def get_all_redirect_rules() -> dict[str, dict[str, Any]]:
    """Get all redirect rules."""
    r = await get_redis()
    raw_data = await r.hgetall(REDIRECT_RULES_KEY)
    return {k: json.loads(v) for k, v in raw_data.items()}


async def get_redirect_conflicts() -> list[dict[str, Any]]:
    """Return all unresolved filename and alias conflicts."""
    r = await get_redis()
    raw_data = await r.hgetall(REDIRECT_CONFLICTS_KEY)
    return [json.loads(value) for _, value in sorted(raw_data.items())]


async def get_manifest_snapshot() -> tuple[
    dict[str, dict[str, Any]],
    dict[str, str],
    list[dict[str, Any]],
]:
    """Read all Manifest inputs in one Redis transaction."""
    r = await get_redis()
    pipeline = r.pipeline(transaction=True)
    try:
        pipeline.get(MANIFEST_METADATA_UPDATE_KEY)
        pipeline.hgetall(REDIRECT_RULES_KEY)
        pipeline.hgetall(VERSION_META_KEY)
        pipeline.hgetall(REDIRECT_CONFLICTS_KEY)
        pipeline.get(MANIFEST_METADATA_UPDATE_KEY)
        before, raw_rules, versions, raw_conflicts, after = await pipeline.execute()
    finally:
        await pipeline.aclose()
    if before or after:
        raise RuntimeError("artifact metadata update is in progress")
    rules = {
        filename: json.loads(value)
        for filename, value in raw_rules.items()
    }
    conflicts = [
        json.loads(value)
        for _, value in sorted(raw_conflicts.items())
    ]
    return rules, versions, conflicts


async def begin_manifest_metadata_update() -> str:
    """Mark a scraper batch so no mixed-batch snapshot can be published."""
    token = uuid.uuid4().hex
    r = await get_redis()
    acquired = await r.set(
        MANIFEST_METADATA_UPDATE_KEY,
        token,
        ex=MANIFEST_METADATA_UPDATE_TTL_SECONDS,
        nx=True,
    )
    if not acquired:
        raise RuntimeError("another artifact metadata update is already in progress")
    return token


async def refresh_manifest_metadata_update(token: str) -> bool:
    """Refresh the batch marker only while it still belongs to the caller."""
    r = await get_redis()
    refreshed = await r.eval(
        """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('expire', KEYS[1], ARGV[2])
        end
        return 0
        """,
        1,
        MANIFEST_METADATA_UPDATE_KEY,
        token,
        MANIFEST_METADATA_UPDATE_TTL_SECONDS,
    )
    return bool(refreshed)


async def end_manifest_metadata_update(token: str) -> None:
    """Clear the current batch marker only when it still belongs to the caller."""
    r = await get_redis()
    await r.eval(
        """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        end
        return 0
        """,
        1,
        MANIFEST_METADATA_UPDATE_KEY,
        token,
    )


async def delete_redirect_rules_by_source(source: str):
    """Delete all redirect rules from a specific source."""
    r = await get_redis()
    all_rules = await get_all_redirect_rules()
    keys_to_delete = [k for k, v in all_rules.items() if v.get("source") == source]
    if keys_to_delete:
        await r.hdel(REDIRECT_RULES_KEY, *keys_to_delete)
    raw_aliases = await r.hgetall(REDIRECT_ALIASES_KEY)
    aliases_to_delete = [
        alias
        for alias, value in raw_aliases.items()
        if json.loads(value).get("source") == source
    ]
    if aliases_to_delete:
        await r.hdel(REDIRECT_ALIASES_KEY, *aliases_to_delete)


async def replace_redirect_rules_for_source(
    source: str,
    resources: list[dict[str, Any]],
) -> None:
    """Replace one scraper's rules without a delete-before-write outage."""
    existing = await get_all_redirect_rules()
    seen: set[str] = set()
    for resource in resources:
        filename = resource["filename"]
        seen.add(filename)
        await set_redirect_rule(**resource)

    r = await get_redis()
    stale = [
        filename
        for filename, rule in existing.items()
        if rule.get("source") == source and filename not in seen
    ]
    if stale:
        await r.hdel(REDIRECT_RULES_KEY, *stale)
    raw_aliases = await r.hgetall(REDIRECT_ALIASES_KEY)
    stale_aliases = [
        alias
        for alias, value in raw_aliases.items()
        if (
            json.loads(value).get("source") == source
            and json.loads(value).get("canonical_filename") not in seen
        )
    ]
    if stale_aliases:
        await r.hdel(REDIRECT_ALIASES_KEY, *stale_aliases)


async def migrate_redis_schema() -> int:
    """Idempotently add v2 defaults to existing v1 redirect rules."""
    r = await get_redis()
    raw_version = await r.get(REDIS_SCHEMA_VERSION_KEY)
    try:
        version = int(raw_version or 1)
    except (TypeError, ValueError):
        logger.warning("Invalid Redis schema version %r; treating as v1", raw_version)
        version = 1
    if version >= REDIS_SCHEMA_VERSION:
        return version

    raw_rules = await r.hgetall(REDIRECT_RULES_KEY)
    for filename, raw_rule in raw_rules.items():
        try:
            rule = json.loads(raw_rule)
        except (TypeError, json.JSONDecodeError):
            logger.warning("Skipping malformed Redis redirect rule: %s", filename)
            continue
        scalar_checksum = rule.get("checksum")
        scalar_algorithm = normalize_algorithm(rule.get("checksum_type"))
        raw_checksums = rule.get("checksums") or {}
        had_checksum_input = bool(scalar_checksum or raw_checksums)
        normalized_checksums: dict[str, str] = {}
        for raw_algorithm, raw_digest in raw_checksums.items():
            algorithm = normalize_algorithm(raw_algorithm)
            if algorithm and validate_checksum(algorithm, raw_digest):
                normalized_checksums[algorithm] = raw_digest.strip().lower()
        if (
            scalar_checksum
            and scalar_algorithm
            and validate_checksum(scalar_algorithm, scalar_checksum)
        ):
            normalized_checksums[scalar_algorithm] = (
                scalar_checksum.strip().lower()
            )
        selected_checksum = choose_strongest(normalized_checksums)
        rule["checksums"] = normalized_checksums
        if selected_checksum:
            rule["checksum_type"], rule["checksum"] = selected_checksum
            rule["checksum_unavailable_reason"] = None
        else:
            rule.setdefault("checksum", None)
            rule.setdefault("checksum_type", None)
            rule.setdefault(
                "checksum_unavailable_reason",
                (
                    "invalid_upstream_checksum_format"
                    if had_checksum_input
                    else "upstream_not_published"
                ),
            )
        rule.setdefault("kind", "source")
        rule.setdefault("platform", {"os": "any", "arch": "any", "libc": None})
        rule.setdefault("channel", "unknown")
        rule.setdefault("aliases", [])
        rule.setdefault("checksum_source_url", None)
        rule.setdefault("component", None)
        await r.hset(REDIRECT_RULES_KEY, filename, json.dumps(rule, sort_keys=True))
    await r.set(REDIS_SCHEMA_VERSION_KEY, REDIS_SCHEMA_VERSION)
    return REDIS_SCHEMA_VERSION


async def set_version_meta(key: str, version: str):
    """Set version metadata."""
    r = await get_redis()
    await r.hset(VERSION_META_KEY, key, version)


async def get_version_meta(key: str) -> str | None:
    """Get version metadata."""
    r = await get_redis()
    return await r.hget(VERSION_META_KEY, key)


async def get_all_version_metas() -> dict[str, str]:
    """Get all version metadata."""
    r = await get_redis()
    return await r.hgetall(VERSION_META_KEY)


async def set_scheduler_times(last_run: datetime | None = None, next_run: datetime | None = None):
    """Update scheduler run times."""
    r = await get_redis()
    if last_run:
        await r.set(SCHEDULER_LAST_RUN_KEY, last_run.isoformat())
    if next_run:
        await r.set(SCHEDULER_NEXT_RUN_KEY, next_run.isoformat())


async def get_scheduler_times() -> dict[str, str | None]:
    """Get scheduler run times."""
    r = await get_redis()
    return {
        "last_run": await r.get(SCHEDULER_LAST_RUN_KEY),
        "next_run": await r.get(SCHEDULER_NEXT_RUN_KEY),
    }


async def set_manifest_status(status: dict[str, Any]) -> None:
    """Persist the most recent manifest build status."""
    r = await get_redis()
    await r.set(MANIFEST_STATUS_KEY, json.dumps(status, sort_keys=True))


async def get_manifest_status() -> dict[str, Any]:
    """Read the most recent manifest build status."""
    r = await get_redis()
    raw = await r.get(MANIFEST_STATUS_KEY)
    return json.loads(raw) if raw else {}


async def get_manifest_events(limit: int = 20) -> list[dict[str, Any]]:
    """Read recent manifest/cache integrity events."""
    if limit <= 0:
        return []
    r = await get_redis()
    raw = await r.lrange(MANIFEST_EVENTS_KEY, 0, limit - 1)
    return [json.loads(value) for value in raw]
