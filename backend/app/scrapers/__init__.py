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
# Web servers
from . import nginx
from . import httpd
from . import openresty
from . import tengine

# Databases
from . import mysql
from . import mariadb
from . import postgresql
from . import redis_scraper

# PHP related
from . import php
from . import phpmyadmin
from . import php_plugins
from . import php_patches
from . import cphalcon

# Libraries and tools
from . import curl
from . import openssl
from . import nghttp2
from . import apr
from . import imagemagick
from . import graphicsmagick
from . import freetype
from . import libiconv
from . import boost
from . import bison
from . import binutils

# Languages
from . import python
from . import pip

# Cache
from . import memcached
from . import xcache

# Security and utilities
from . import fail2ban
from . import cacert
from . import acme_sh
from . import pure_ftpd
from . import htop

# Lua modules
from . import lua_nginx_module

# Misc GitHub repos
from . import misc_github

# Misc static/pinned resources (SourceGuardian, IonCube, pcre, libmcrypt, etc.)
from . import misc

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
