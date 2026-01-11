"""
Redirect router for public file redirects.
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse, PlainTextResponse

from app.services import redirect_service

router = APIRouter(tags=["Redirect"])


@router.get("/src/{filename:path}")
async def redirect_file(filename: str):
    """
    Redirect to the actual file download URL.
    
    This is the main endpoint used by OneinStack scripts.
    """
    url = await redirect_service.get_redirect_url(filename)
    
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found in redirect rules",
        )
    
    return RedirectResponse(url=url, status_code=status.HTTP_301_MOVED_PERMANENTLY)


@router.get("/oneinstack/src/{filename:path}")
async def redirect_file_legacy(filename: str):
    """
    Legacy redirect path for compatibility.
    
    Redirects /oneinstack/src/file.tar.gz to the actual URL.
    """
    url = await redirect_service.get_redirect_url(filename)
    
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found in redirect rules",
        )
    
    return RedirectResponse(url=url, status_code=status.HTTP_301_MOVED_PERMANENTLY)


@router.get("/suggest_versions.txt", response_class=PlainTextResponse)
async def get_suggest_versions():
    """
    Get suggested versions file.
    
    Returns a plain text file with version suggestions for OneinStack.
    Format: key=version per line.
    """
    content = await redirect_service.get_suggest_versions_content()
    return PlainTextResponse(content=content)
