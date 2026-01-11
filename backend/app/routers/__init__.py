"""
Routers package.
"""
from .auth import router as auth_router
from .settings import router as settings_router
from .resources import router as resources_router
from .redirect import router as redirect_router
from .scraper import router as scraper_router

__all__ = [
    "auth_router",
    "settings_router",
    "resources_router",
    "redirect_router",
    "scraper_router",
]
