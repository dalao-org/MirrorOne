"""
Setting service for managing system configuration.
"""
import json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.setting import Setting


# Default settings to initialize
DEFAULT_SETTINGS = [
    {
        "key": "mirror_type",
        "value": "redirect",
        "value_type": "string",
        "description": "Mirror mode: 'redirect' (use original URLs) or 'cache' (download and serve locally)",
    },
    {
        "key": "cache_path",
        "value": "/app/cache",
        "value_type": "string",
        "description": "Path to cache directory for downloaded files",
    },
    {
        "key": "github_api_token",
        "value": "",
        "value_type": "string",
        "description": "GitHub API Token for increased rate limits",
    },
    {
        "key": "php_accepted_versions",
        "value": '["8.1", "8.2", "8.3", "8.4"]',
        "value_type": "json",
        "description": "List of PHP versions to track",
    },
    {
        "key": "scrape_interval_hours",
        "value": "6",
        "value_type": "int",
        "description": "Hours between automatic scrape runs",
    },
    {
        "key": "nginx_legacy_versions_count",
        "value": "5",
        "value_type": "int",
        "description": "Number of legacy Nginx versions to track",
    },
    {
        "key": "enable_auto_scrape",
        "value": "true",
        "value_type": "bool",
        "description": "Enable automatic scheduled scraping",
    },
    # MySQL settings
    {
        "key": "mysql_accepted_versions",
        "value": '["5.5", "5.6", "5.7", "8.0", "8.4", "9.0", "9.1"]',
        "value_type": "json",
        "description": "List of MySQL versions to track",
    },
    {
        "key": "mysql_blacklist",
        "value": '["arm", "32-bit", "test", "minimal", "ia-64", "debug"]',
        "value_type": "json",
        "description": "MySQL package blacklist keywords",
    },
    # Python settings
    {
        "key": "python_accepted_versions",
        "value": '["2.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]',
        "value_type": "json",
        "description": "List of Python versions to track",
    },
    # MariaDB settings
    {
        "key": "mariadb_accepted_versions",
        "value": '["5.5", "10.4", "10.5", "10.11", "11.4"]',
        "value_type": "json",
        "description": "List of MariaDB versions to track",
    },
    # Apache HTTPD settings
    {
        "key": "httpd_blacklist",
        "value": '["alpha", "beta", "deps", "rc"]',
        "value_type": "json",
        "description": "Apache HTTPD version blacklist",
    },
    # APR settings
    {
        "key": "apr_blacklist",
        "value": '["alpha", "beta", "deps", "rc", "win32"]',
        "value_type": "json",
        "description": "APR version blacklist",
    },
    # pip/setuptools settings
    {
        "key": "pip_blacklist",
        "value": '["test", "b1", "b2", "b3", "a1", "a2", "rc"]',
        "value_type": "json",
        "description": "pip/setuptools version blacklist",
    },
    # PHP plugins settings
    {
        "key": "php_plugins_blacklist",
        "value": '["alpha", "beta", "rc", "test"]',
        "value_type": "json",
        "description": "PHP plugins version blacklist",
    },
    # GitHub settings
    {
        "key": "github_blacklist",
        "value": '["rc", "beta", "alpha", "dev", "preview"]',
        "value_type": "json",
        "description": "GitHub releases/tags blacklist",
    },
    # misc_github settings
    {
        "key": "misc_github_max_versions",
        "value": "5",
        "value_type": "int",
        "description": "Number of versions to mirror for misc GitHub projects (jemalloc, icu4c, libzip, etc.). Set to 0 to mirror all versions.",
    },
]


def _parse_value(value: str | None, value_type: str) -> Any:
    """Parse stored string value to appropriate type."""
    if value is None:
        return None
    
    if value_type == "json":
        return json.loads(value)
    elif value_type == "int":
        return int(value)
    elif value_type == "bool":
        return value.lower() in ("true", "1", "yes")
    else:
        return value


def _serialize_value(value: Any, value_type: str) -> str:
    """Serialize value to string for storage."""
    if value_type == "json":
        return json.dumps(value)
    elif value_type == "bool":
        return "true" if value else "false"
    else:
        return str(value)


async def init_default_settings(db: AsyncSession) -> None:
    """
    Initialize default settings if they don't exist.
    
    Args:
        db: Database session
    """
    for setting_data in DEFAULT_SETTINGS:
        result = await db.execute(
            select(Setting).where(Setting.key == setting_data["key"])
        )
        existing = result.scalar_one_or_none()
        
        if existing is None:
            setting = Setting(**setting_data)
            db.add(setting)
    
    await db.commit()


async def get_all_settings(db: AsyncSession) -> dict[str, Any]:
    """
    Get all settings as a dictionary.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary of setting key to parsed value
    """
    result = await db.execute(select(Setting))
    settings = result.scalars().all()
    
    return {
        setting.key: _parse_value(setting.value, setting.value_type)
        for setting in settings
    }


async def get_all_settings_full(db: AsyncSession) -> list[Setting]:
    """
    Get all settings as full Setting objects.
    
    Args:
        db: Database session
        
    Returns:
        List of Setting objects
    """
    result = await db.execute(select(Setting))
    return list(result.scalars().all())


async def get_setting(db: AsyncSession, key: str) -> Any | None:
    """
    Get a single setting value by key.
    
    Args:
        db: Database session
        key: Setting key
        
    Returns:
        Parsed setting value or None
    """
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    
    if setting is None:
        return None
    
    return _parse_value(setting.value, setting.value_type)


async def update_setting(db: AsyncSession, key: str, value: Any) -> Setting | None:
    """
    Update a setting value.
    
    Args:
        db: Database session
        key: Setting key
        value: New value
        
    Returns:
        Updated Setting object or None if not found
    """
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    
    if setting is None:
        return None
    
    setting.value = _serialize_value(value, setting.value_type)
    await db.commit()
    await db.refresh(setting)
    
    return setting
