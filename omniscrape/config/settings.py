"""
OmniScrape Engine - Configuration Settings
Centralized configuration management using Pydantic Settings
"""

from functools import lru_cache
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "OmniScrape Engine"
    app_version: str = "1.0.0"
    app_env: str = "production"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Concurrency
    max_concurrent_serp_scrapes: int = 60
    max_concurrent_deep_scrapes: int = 30
    request_timeout: int = 30
    connect_timeout: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None
    cache_ttl: int = 3600
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Proxy
    proxy_list_url: str = "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
    proxy_validation_timeout: int = 5
    proxy_pool_size: int = 50
    custom_proxy_url: Optional[str] = None
    proxy_rotation_interval: int = 30
    
    # Browser
    headless_mode: bool = True
    browser_timeout: int = 30000
    max_browser_instances: int = 5
    stealth_mode: bool = True
    
    # Crawler
    max_crawl_depth: int = 3
    max_pages_per_crawl: int = 100
    crawl_delay_min: float = 1.0
    crawl_delay_max: float = 3.0
    respect_robots_txt: bool = False
    
    # Retry
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff_multiplier: float = 2.0
    
    # CAPTCHA
    captcha_solve_timeout: int = 60
    enable_local_captcha_solver: bool = True
    ocr_engine: str = "tesseract"
    
    # Anti-Detection
    rotate_user_agent: bool = True
    rotate_fingerprint: bool = True
    spoof_headers: bool = True
    tls_fingerprint_chrome: bool = True
    
    # Search Engine Delays
    google_delay: float = 2.0
    bing_delay: float = 1.0
    duckduckgo_delay: float = 0.5
    yahoo_delay: float = 1.5
    yandex_delay: float = 2.0
    
    # Data Mining
    extract_emails: bool = True
    extract_phones: bool = True
    extract_social_links: bool = True
    extract_schema_org: bool = True
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience access
settings = get_settings()
