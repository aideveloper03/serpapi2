"""
OmniScrape Engine - Structured Logging
Production-grade logging with trace IDs and structured output
"""

import sys
import uuid
import logging
from typing import Optional, Any, Dict
from contextvars import ContextVar
from functools import wraps
import structlog
from structlog.types import Processor

# Context variable for request tracing
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def generate_trace_id() -> str:
    """Generate a unique trace ID"""
    return str(uuid.uuid4())[:8]


def add_trace_context(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add trace context to log entries"""
    trace_id = trace_id_var.get()
    request_id = request_id_var.get()
    
    if trace_id:
        event_dict["trace_id"] = trace_id
    if request_id:
        event_dict["request_id"] = request_id
    
    return event_dict


def add_service_context(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add service context to log entries"""
    event_dict["service"] = "omniscrape"
    event_dict["version"] = "1.0.0"
    return event_dict


def setup_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    """Configure structured logging for the application"""
    
    # Define processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_trace_context,
        add_service_context,
    ]
    
    if json_format:
        # Production: JSON format
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Console format
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Also configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name or __name__)


class LogContext:
    """Context manager for adding temporary log context"""
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.token = None
    
    def __enter__(self):
        structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        structlog.contextvars.unbind_contextvars(*self.context.keys())


def log_execution(func):
    """Decorator to log function execution with timing"""
    import time
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start = time.perf_counter()
        
        logger.info(
            "function_start",
            function=func.__name__,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys()),
        )
        
        try:
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            logger.info(
                "function_complete",
                function=func.__name__,
                duration_ms=round(elapsed * 1000, 2),
            )
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.error(
                "function_error",
                function=func.__name__,
                duration_ms=round(elapsed * 1000, 2),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start = time.perf_counter()
        
        logger.info(
            "function_start",
            function=func.__name__,
        )
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            logger.info(
                "function_complete",
                function=func.__name__,
                duration_ms=round(elapsed * 1000, 2),
            )
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.error(
                "function_error",
                function=func.__name__,
                duration_ms=round(elapsed * 1000, 2),
                error=str(e),
            )
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# Initialize logging on import
logger = get_logger("omniscrape")
