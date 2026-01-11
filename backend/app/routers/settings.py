"""
Settings router.
"""
from fastapi import APIRouter, HTTPException, status
from typing import Any

from app.core.dependencies import DbSession, CurrentUser
from app.schemas.setting import SettingResponse, SettingUpdate
from app.services import setting_service

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=list[SettingResponse])
async def get_all_settings(current_user: CurrentUser, db: DbSession):
    """
    Get all system settings.
    
    Requires authentication.
    """
    settings = await setting_service.get_all_settings_full(db)
    
    # Parse values for response
    result = []
    for setting in settings:
        parsed_value = setting_service._parse_value(setting.value, setting.value_type)
        result.append(SettingResponse(
            id=setting.id,
            key=setting.key,
            value=parsed_value,
            value_type=setting.value_type,
            description=setting.description,
            updated_at=setting.updated_at,
        ))
    
    return result


@router.get("/{key}")
async def get_setting(key: str, current_user: CurrentUser, db: DbSession) -> dict[str, Any]:
    """
    Get a single setting by key.
    
    Requires authentication.
    """
    value = await setting_service.get_setting(db, key)
    
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )
    
    return {"key": key, "value": value}


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    update: SettingUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Update a setting value.
    
    Requires authentication.
    """
    setting = await setting_service.update_setting(db, key, update.value)
    
    if setting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )
    
    parsed_value = setting_service._parse_value(setting.value, setting.value_type)
    
    return SettingResponse(
        id=setting.id,
        key=setting.key,
        value=parsed_value,
        value_type=setting.value_type,
        description=setting.description,
        updated_at=setting.updated_at,
    )
