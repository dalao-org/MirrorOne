"""
Application configuration using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Oneinstack Mirror Generator"
    APP_VERSION: str = "2.1.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./data/app.db")
    
    # Redis
    REDIS_URL: str = Field(default="redis://redis:6379/0")
    
    # Security
    SECRET_KEY: str = Field(default="change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    
    # Admin (initial setup)
    ADMIN_USERNAME: str = Field(default="admin")
    ADMIN_PASSWORD: str = Field(default="")  # Must be set in production
    
    # CORS
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    # Artifact manifest
    MANIFEST_ENABLED: bool = True
    MANIFEST_OUTPUT_DIR: str = "/app/data/manifests"
    MANIFEST_PUBLIC_BASE_URL: str = "http://localhost:3000"
    MANIFEST_REBUILD_AFTER_SCRAPE: bool = True
    MANIFEST_INCLUDE_CACHE_STATUS: bool = True
    MANIFEST_KEEP_HISTORY: int = 20
    MANIFEST_CHECKSUM_SIDECAR: bool = True
    MANIFEST_GENERATOR_COMMIT: str = "unknown"
    MANIFEST_INSTANCE_ID: str = "mirrorone"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
