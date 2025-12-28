"""
OmniScrape Engine - Health Check Endpoints
System health and monitoring endpoints
"""

import time
from fastapi import APIRouter
from typing import Dict, Any

from models import HealthResponse
from services import proxy_manager
from config import settings
from utils import get_logger

logger = get_logger(__name__)

# Track server start time
_start_time = time.time()
_active_requests = 0

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of the API",
)
async def health_check() -> HealthResponse:
    """Get system health status"""
    # Check Redis connection
    redis_connected = await _check_redis()
    
    return HealthResponse(
        status="healthy" if redis_connected else "degraded",
        version=settings.app_version,
        uptime_seconds=time.time() - _start_time,
        redis_connected=redis_connected,
        proxy_pool_size=proxy_manager.pool_size_current,
        active_requests=_active_requests,
    )


@router.get(
    "/health/detailed",
    summary="Detailed Health Check",
    description="Get detailed system health information",
)
async def detailed_health() -> Dict[str, Any]:
    """Get detailed health information"""
    redis_connected = await _check_redis()
    proxy_stats = proxy_manager.get_stats()
    
    return {
        "status": "healthy" if redis_connected else "degraded",
        "version": settings.app_version,
        "environment": settings.app_env,
        "uptime_seconds": time.time() - _start_time,
        "components": {
            "redis": {
                "connected": redis_connected,
                "url": settings.redis_url.split("@")[-1] if "@" in settings.redis_url else settings.redis_url,
            },
            "proxy_manager": proxy_stats,
            "rate_limiter": {
                "limit": settings.rate_limit_requests,
                "window_seconds": settings.rate_limit_window,
            },
        },
        "configuration": {
            "max_concurrent_serp_scrapes": settings.max_concurrent_serp_scrapes,
            "max_concurrent_deep_scrapes": settings.max_concurrent_deep_scrapes,
            "request_timeout": settings.request_timeout,
            "browser_timeout": settings.browser_timeout,
            "max_crawl_depth": settings.max_crawl_depth,
            "stealth_mode": settings.stealth_mode,
        },
        "active_requests": _active_requests,
    }


@router.get(
    "/ready",
    summary="Readiness Check",
    description="Check if the service is ready to accept traffic",
)
async def readiness_check() -> Dict[str, bool]:
    """Check if service is ready"""
    # Check critical dependencies
    redis_ok = await _check_redis()
    proxy_ok = proxy_manager.pool_size_current > 0 or settings.custom_proxy_url
    
    ready = redis_ok or not settings.redis_url  # Redis optional if not configured
    
    return {
        "ready": ready,
        "redis": redis_ok,
        "proxy_pool": proxy_ok,
    }


@router.get(
    "/live",
    summary="Liveness Check",
    description="Check if the service is alive",
)
async def liveness_check() -> Dict[str, str]:
    """Simple liveness check"""
    return {"status": "alive"}


async def _check_redis() -> bool:
    """Check Redis connection"""
    try:
        import redis.asyncio as redis
        
        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.close()
        return True
    except Exception:
        return False


def increment_active_requests():
    """Increment active request counter"""
    global _active_requests
    _active_requests += 1


def decrement_active_requests():
    """Decrement active request counter"""
    global _active_requests
    _active_requests = max(0, _active_requests - 1)
