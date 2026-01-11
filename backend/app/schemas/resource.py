"""
Resource schemas.
"""
from pydantic import BaseModel
from datetime import datetime


class Resource(BaseModel):
    """Resource schema for redirect rules."""
    file_name: str
    url: str
    version: str
    checksum: str | None = None
    checksum_type: str | None = None
    source: str
    updated_at: datetime | None = None


class VersionMeta(BaseModel):
    """Version metadata schema."""
    key: str
    version: str


class RedirectRule(BaseModel):
    """Redirect rule from Redis."""
    file_name: str
    url: str
    version: str
    source: str
    updated_at: str


class ResourceListResponse(BaseModel):
    """Response for resource listing."""
    total: int
    resources: list[RedirectRule]


class VersionMetaListResponse(BaseModel):
    """Response for version metadata listing."""
    versions: dict[str, str]
