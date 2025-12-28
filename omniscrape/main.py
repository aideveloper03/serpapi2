"""
OmniScrape Engine - Main Application
Production-ready web scraping API
"""

import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure uvloop for maximum performance
try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

from config import settings
from utils import setup_logging, get_logger
from api import v1_router
from middleware import RateLimitMiddleware, LoggingMiddleware
from services import proxy_manager

# Setup logging
setup_logging(settings.log_level, json_format=settings.app_env == "production")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info(
        "app_startup",
        name=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
    )
    
    # Initialize proxy manager
    try:
        await proxy_manager.initialize()
    except Exception as e:
        logger.warning("proxy_manager_init_failed", error=str(e))
    
    # Install Playwright browsers if needed
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            # This will trigger browser download if not present
            pass
    except Exception as e:
        logger.warning("playwright_init_info", message=str(e))
    
    logger.info("app_ready")
    
    yield
    
    # Shutdown
    logger.info("app_shutdown")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
# OmniScrape Engine

**Production-ready, high-volume web and search engine scraping API.**

## Features

- 🔍 **Multi-Engine Search**: Google, Bing, DuckDuckGo, Yahoo, Yandex
- 🔄 **Cascading Fallback**: Automatic failover between engines
- 🕷️ **Deep Web Scraping**: Content extraction with categorization
- 🛡️ **Anti-Detection**: Fingerprint rotation, proxy management, CAPTCHA handling
- 👻 **GhostNet Protocol**: Novel undetectable crawling techniques
- ⚡ **High Performance**: 60+ SERP scrapes/min, 30+ deep scrapes/min
- 📊 **Structured Data**: Schema.org, OpenGraph, metadata extraction
- 📧 **Data Mining**: Email, phone, social link extraction

## API Sections

- `/api/v1/search` - Search engine scraping
- `/api/v1/crawl` - Deep web crawling
- `/api/v1/mine` - Data mining and extraction
- `/health` - System health checks

## Anti-Detection Techniques

1. **Browser Fingerprinting**: Rotating User-Agent, Sec-Ch-Ua, and headers
2. **TLS Fingerprinting**: Chrome TLS signature mimicking via curl-cffi
3. **Proxy Rotation**: Real-time proxy validation and rotation
4. **IP Spoofing**: X-Forwarded-For and Via header manipulation
5. **CAPTCHA Handling**: Local solving for simple CAPTCHAs
6. **Behavioral Mimicking**: Human-like timing and navigation patterns
""",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    rate=settings.rate_limit_requests,
    window=settings.rate_limit_window,
)

# Include API routers
app.include_router(v1_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Production-ready web and search engine scraping API",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        },
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
