"""
Scraper registry for managing and running scrapers.
"""
from typing import Type, Any
import httpx

from .base import BaseScraper, ScrapeResult


class ScraperRegistry:
    """
    Registry for scraper classes.
    
    Use the @registry.register decorator to register scrapers.
    """
    
    _scrapers: dict[str, Type[BaseScraper]] = {}
    
    @classmethod
    def register(cls, name: str):
        """
        Decorator to register a scraper class.
        
        Usage:
            @registry.register("nginx")
            class NginxScraper(BaseScraper):
                ...
        """
        def decorator(scraper_class: Type[BaseScraper]):
            cls._scrapers[name] = scraper_class
            scraper_class.name = name
            return scraper_class
        return decorator
    
    @classmethod
    def get_all_names(cls) -> list[str]:
        """Get list of all registered scraper names."""
        return list(cls._scrapers.keys())
    
    @classmethod
    def get_scraper_class(cls, name: str) -> Type[BaseScraper] | None:
        """Get scraper class by name."""
        return cls._scrapers.get(name)
    
    @classmethod
    async def run_all(cls, settings: dict[str, Any]) -> list[ScrapeResult]:
        """
        Run all registered scrapers.
        
        Args:
            settings: Settings dictionary from database
            
        Returns:
            List of ScrapeResult from all scrapers
        """
        results = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for name, scraper_class in cls._scrapers.items():
                scraper = scraper_class(settings, client)
                result = await scraper.safe_scrape()
                results.append(result)
        return results
    
    @classmethod
    async def run_one(cls, name: str, settings: dict[str, Any]) -> ScrapeResult | None:
        """
        Run a single scraper by name.
        
        Args:
            name: Scraper name
            settings: Settings dictionary from database
            
        Returns:
            ScrapeResult or None if scraper not found
        """
        scraper_class = cls._scrapers.get(name)
        if scraper_class is None:
            return None
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            scraper = scraper_class(settings, client)
            return await scraper.safe_scrape()


# Global registry instance
registry = ScraperRegistry()
