"""
OmniScrape Engine - Rate Limiter Middleware
Redis-based rate limiting for API endpoints
"""

import asyncio
import time
from typing import Optional, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import HTTPException

from config import settings
from utils import get_logger

logger = get_logger(__name__)


class TokenBucket:
    """Token bucket rate limiter implementation"""
    
    def __init__(
        self,
        rate: int,
        window: int,
        redis_client=None,
    ):
        self.rate = rate  # Requests per window
        self.window = window  # Window in seconds
        self.redis_client = redis_client
        self._local_buckets: dict = {}
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str) -> tuple[bool, dict]:
        """Check if request is allowed under rate limit"""
        if self.redis_client:
            return await self._check_redis(key)
        return await self._check_local(key)
    
    async def _check_redis(self, key: str) -> tuple[bool, dict]:
        """Check rate limit using Redis"""
        try:
            now = time.time()
            window_start = int(now) - (int(now) % self.window)
            redis_key = f"ratelimit:{key}:{window_start}"
            
            # Use Redis pipeline for atomicity
            async with self.redis_client.pipeline() as pipe:
                pipe.incr(redis_key)
                pipe.expire(redis_key, self.window + 1)
                results = await pipe.execute()
            
            current = results[0]
            remaining = max(0, self.rate - current)
            reset_at = window_start + self.window
            
            info = {
                "limit": self.rate,
                "remaining": remaining,
                "reset": reset_at,
                "retry_after": reset_at - now if current > self.rate else None,
            }
            
            return current <= self.rate, info
            
        except Exception as e:
            logger.warning("redis_rate_limit_error", error=str(e))
            # Fall back to local on Redis error
            return await self._check_local(key)
    
    async def _check_local(self, key: str) -> tuple[bool, dict]:
        """Check rate limit using local storage"""
        async with self._lock:
            now = time.time()
            window_start = int(now) - (int(now) % self.window)
            bucket_key = f"{key}:{window_start}"
            
            # Clean old entries
            old_keys = [
                k for k in self._local_buckets
                if int(k.split(":")[-1]) < window_start - self.window
            ]
            for old_key in old_keys:
                del self._local_buckets[old_key]
            
            # Check current window
            current = self._local_buckets.get(bucket_key, 0)
            self._local_buckets[bucket_key] = current + 1
            
            remaining = max(0, self.rate - current - 1)
            reset_at = window_start + self.window
            
            info = {
                "limit": self.rate,
                "remaining": remaining,
                "reset": reset_at,
                "retry_after": reset_at - now if current >= self.rate else None,
            }
            
            return current < self.rate, info


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(
        self,
        app,
        rate: int = 100,
        window: int = 60,
        redis_client=None,
        key_func: Optional[Callable] = None,
    ):
        super().__init__(app)
        self.limiter = TokenBucket(rate, window, redis_client)
        self.key_func = key_func or self._default_key_func
    
    def _default_key_func(self, request: Request) -> str:
        """Default key function using client IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        return f"ip:{ip}"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for certain paths
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        key = self.key_func(request)
        allowed, info = await self.limiter.is_allowed(key)
        
        # Add rate limit headers to response
        response_headers = {
            "X-RateLimit-Limit": str(info["limit"]),
            "X-RateLimit-Remaining": str(info["remaining"]),
            "X-RateLimit-Reset": str(int(info["reset"])),
        }
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "retry_after": info["retry_after"],
                },
                headers={
                    **response_headers,
                    "Retry-After": str(int(info["retry_after"])),
                },
            )
        
        response = await call_next(request)
        
        # Add headers to successful response
        for header, value in response_headers.items():
            response.headers[header] = value
        
        return response


# Default rate limiter instance
rate_limiter = TokenBucket(
    rate=settings.rate_limit_requests,
    window=settings.rate_limit_window,
)
