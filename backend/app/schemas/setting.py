"""
Setting schemas.
"""
from pydantic import BaseModel
from typing import Any
from datetime import datetime


class SettingBase(BaseModel):
    """Base setting schema."""
    key: str
    value: Any
    description: str | None = None


class SettingResponse(BaseModel):
    """Setting response schema."""
    id: int
    key: str
    value: Any
    value_type: str
    description: str | None
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class SettingUpdate(BaseModel):
    """Setting update schema."""
    value: Any


class SettingCreate(BaseModel):
    """Setting create schema."""
    key: str
    value: Any
    value_type: str = "string"
    description: str | None = None
