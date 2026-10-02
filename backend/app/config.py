"""Configuration settings for the application."""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/cholera_surveillance"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_ssl_mode: str = "require"

    # Google Earth Engine
    gee_service_account_email: Optional[str] = None
    gee_private_key_path: Optional[str] = None
    gee_service_account_json: Optional[str] = None
    # Earth Engine project id for ADC-based auth (no exported SA key required)
    ee_project: Optional[str] = None

    # NASA Earthdata
    nasa_earthdata_username: Optional[str] = None
    nasa_earthdata_password: Optional[str] = None

    # OpenWeatherMap
    openweathermap_api_key: Optional[str] = None

    # App settings
    debug: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:3000,https://flooding-cholera.vercel.app"

    # Rate limiting
    rate_limit_requests: int = 100  # requests per minute for general endpoints
    rate_limit_upload: int = 10  # requests per minute for upload endpoints

    # External API timeouts (in seconds)
    external_api_timeout: int = 30
    satellite_api_timeout: int = 60

    # Sentry
    sentry_dsn: Optional[str] = None
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1

    # AI Provider API Keys (optional — copilot falls back to mock mode if absent)
    gemini_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    nvidia_nim_api_key: Optional[str] = None

    # Cross River State bounding box (approximate)
    crs_bbox: dict = {
        "min_lon": 7.5,
        "max_lon": 9.5,
        "min_lat": 4.5,
        "max_lat": 7.0
    }

    seed_demo: bool = False  # set SEED_DEMO=true to also seed synthetic scenario
    nigeria_bbox: dict = {
        "min_lon": 3.0,
        "max_lon": 15.0,
        "min_lat": 4.0,
        "max_lat": 14.0,
    }

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
