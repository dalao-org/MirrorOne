"""
Redis client for redirect rules and version metadata storage.
"""
import json
from datetime import datetime, UTC
from typing import Any
import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

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
    if data:
        return json.loads(data)
    return None


async def set_redirect_rule(filename: str, url: str, version: str, source: str):
    """
    Set a redirect rule.
    
    Args:
        filename: The filename key
        url: The redirect target URL
        version: Version string
        source: Source scraper name
    """
    r = await get_redis()
    data = json.dumps({
        "url": url,
        "version": version,
        "source": source,
        "updated_at": datetime.now(UTC).isoformat(),
    })
    await r.hset(REDIRECT_RULES_KEY, filename, data)


async def get_all_redirect_rules() -> dict[str, dict[str, Any]]:
    """Get all redirect rules."""
    r = await get_redis()
    raw_data = await r.hgetall(REDIRECT_RULES_KEY)
    return {k: json.loads(v) for k, v in raw_data.items()}


async def delete_redirect_rules_by_source(source: str):
    """Delete all redirect rules from a specific source."""
    r = await get_redis()
    all_rules = await get_all_redirect_rules()
    keys_to_delete = [k for k, v in all_rules.items() if v.get("source") == source]
    if keys_to_delete:
        await r.hdel(REDIRECT_RULES_KEY, *keys_to_delete)


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
