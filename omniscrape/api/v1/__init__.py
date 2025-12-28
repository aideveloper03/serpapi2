"""API v1 module"""
from fastapi import APIRouter
from .search import router as search_router
from .crawl import router as crawl_router
from .data_mining import router as data_mining_router
from .health import router as health_router

router = APIRouter(prefix="/api/v1")
router.include_router(search_router)
router.include_router(crawl_router)
router.include_router(data_mining_router)
router.include_router(health_router)

__all__ = ["router"]