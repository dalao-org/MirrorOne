"""
Scrapers package.

Import all scrapers here to register them with the registry.
"""
from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
from .registry import registry, ScraperRegistry
from .github_utils import (
    get_github_releases,
    get_github_tags,
    filter_blacklist,
    download_repo_by_tag,
    get_packages_from_release,
)

# Import all scrapers to trigger registration
from . import nginx
from . import php
from . import redis_scraper

__all__ = [
    "BaseScraper",
    "Resource",
    "VersionMeta",
    "ScrapeResult",
    "registry",
    "ScraperRegistry",
    "get_github_releases",
    "get_github_tags",
    "filter_blacklist",
    "download_repo_by_tag",
    "get_packages_from_release",
]
