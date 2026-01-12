"""
Redirect service for handling file redirects.
"""
from app import redis_client


async def get_redirect_url(filename: str) -> str | None:
    """
    Get redirect URL for a filename.
    
    Args:
        filename: The filename to look up
        
    Returns:
        Redirect URL or None if not found
    """
    rule = await redis_client.get_redirect_url(filename)
    if rule:
        return rule.get("url")
    return None


async def get_all_resources() -> list[dict]:
    """
    Get all redirect resources.
    
    Returns:
        List of resource dictionaries
    """
    rules = await redis_client.get_all_redirect_rules()
    return [
        {"file_name": k, **v}
        for k, v in rules.items()
    ]


async def get_resources_by_source(source: str) -> list[dict]:
    """
    Get resources filtered by source scraper.
    
    Args:
        source: Scraper name to filter by
        
    Returns:
        List of resource dictionaries
    """
    rules = await redis_client.get_all_redirect_rules()
    return [
        {"file_name": k, **v}
        for k, v in rules.items()
        if v.get("source") == source
    ]


async def get_suggest_versions_content() -> str:
    """
    Generate suggest_versions.txt content.
    
    Returns:
        String content for suggest_versions.txt
    """
    versions = await redis_client.get_all_version_metas()
    lines = [f"{key}={value}" for key, value in sorted(versions.items())]
    return "\n".join(lines)
