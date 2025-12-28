"""
OmniScrape Engine - Logging Middleware
Structured request/response logging with trace IDs
"""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from utils import get_logger, trace_id_var, request_id_var

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured logging of all requests"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate trace and request IDs
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4())[:8])
        request_id = str(uuid.uuid4())[:8]
        
        # Set context variables
        trace_id_var.set(trace_id)
        request_id_var.set(request_id)
        
        # Log request start
        start_time = time.perf_counter()
        
        logger.info(
            "request_start",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params),
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("User-Agent", "")[:100],
            trace_id=trace_id,
            request_id=request_id,
        )
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Log request completion
            logger.info(
                "request_complete",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                trace_id=trace_id,
                request_id=request_id,
            )
            
            # Add trace ID to response headers
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            logger.error(
                "request_error",
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
                trace_id=trace_id,
                request_id=request_id,
            )
            
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"
