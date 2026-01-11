"""
Resources router for viewing cached resources.
"""
from fastapi import APIRouter

from app.core.dependencies import CurrentUser
from app.schemas.resource import ResourceListResponse, VersionMetaListResponse
from app.services import redirect_service
from app import redis_client

router = APIRouter(prefix="/api/resources", tags=["Resources"])


@router.get("", response_model=ResourceListResponse)
async def get_all_resources(current_user: CurrentUser):
    """
    Get all cached resources.
    
    Requires authentication.
    """
    resources = await redirect_service.get_all_resources()
    
    return ResourceListResponse(
        total=len(resources),
        resources=resources,
    )


@router.get("/scraper/{scraper_name}", response_model=ResourceListResponse)
async def get_resources_by_scraper(scraper_name: str, current_user: CurrentUser):
    """
    Get resources from a specific scraper.
    
    Requires authentication.
    """
    resources = await redirect_service.get_resources_by_source(scraper_name)
    
    return ResourceListResponse(
        total=len(resources),
        resources=resources,
    )


@router.get("/versions", response_model=VersionMetaListResponse)
async def get_version_metas(current_user: CurrentUser):
    """
    Get all version metadata.
    
    Requires authentication.
    """
    versions = await redis_client.get_all_version_metas()
    
    return VersionMetaListResponse(versions=versions)
