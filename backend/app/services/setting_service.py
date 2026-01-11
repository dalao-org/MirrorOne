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
