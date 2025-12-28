"""
OmniScrape Engine - Search API Endpoints
Endpoints for search engine scraping with cascading fallback
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional

from models import (
    SearchRequest,
    SearchResponse,
    SearchEngine,
    SearchVertical,
    ErrorResponse,
)
from core.engines import search_orchestrator
from utils import get_logger, generate_trace_id

logger = get_logger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


@router.post(
    "",
    response_model=SearchResponse,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Execute Search Query",
    description="""
    Execute a search query across multiple search engines.
    
    **Features:**
    - Supports Google, Bing, DuckDuckGo, Yahoo, and Yandex
    - Automatic cascading fallback between engines
    - Multiple verticals: All, News, Images, Videos
    - Zero-results guard with regex and browser fallback
    - Proxy rotation and fingerprint spoofing
    
    **Fallback Order (when engine=auto):**
    Google → DuckDuckGo → Bing → Yahoo → Yandex
    """,
)
async def search(request: SearchRequest) -> SearchResponse:
    """Execute a search query with automatic fallback"""
    trace_id = generate_trace_id()
    
    logger.info(
        "search_api_request",
        query=request.query,
        engine=request.engine.value,
        vertical=request.vertical.value,
        trace_id=trace_id,
    )
    
    try:
        response = await search_orchestrator.search(request, trace_id)
        return response
        
    except Exception as e:
        logger.error(
            "search_api_error",
            query=request.query,
            error=str(e),
            trace_id=trace_id,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e),
                "error_code": "SEARCH_ERROR",
                "trace_id": trace_id,
            },
        )


@router.get(
    "",
    response_model=SearchResponse,
    summary="Quick Search",
    description="Simplified GET endpoint for quick searches",
)
async def quick_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    engine: SearchEngine = Query(default=SearchEngine.AUTO, description="Search engine"),
    vertical: SearchVertical = Query(default=SearchVertical.ALL, description="Search vertical"),
    num: int = Query(default=10, ge=1, le=100, description="Number of results"),
    page: int = Query(default=1, ge=1, le=50, description="Page number"),
    country: Optional[str] = Query(default=None, max_length=2, description="Country code"),
    language: Optional[str] = Query(default=None, max_length=5, description="Language code"),
    time_range: Optional[str] = Query(default=None, description="Time range: d, w, m, y"),
    safe: bool = Query(default=True, description="Safe search"),
) -> SearchResponse:
    """Execute a search query via GET parameters"""
    request = SearchRequest(
        query=q,
        engine=engine,
        vertical=vertical,
        num_results=num,
        page=page,
        country=country,
        language=language,
        time_range=time_range,
        safe_search=safe,
    )
    return await search(request)


@router.post(
    "/google",
    response_model=SearchResponse,
    summary="Google Search",
    description="Search Google specifically (with fallback if blocked)",
)
async def google_search(request: SearchRequest) -> SearchResponse:
    """Search Google specifically"""
    request.engine = SearchEngine.GOOGLE
    return await search(request)


@router.post(
    "/bing",
    response_model=SearchResponse,
    summary="Bing Search",
    description="Search Bing specifically",
)
async def bing_search(request: SearchRequest) -> SearchResponse:
    """Search Bing specifically"""
    request.engine = SearchEngine.BING
    return await search(request)


@router.post(
    "/duckduckgo",
    response_model=SearchResponse,
    summary="DuckDuckGo Search",
    description="Search DuckDuckGo specifically",
)
async def duckduckgo_search(request: SearchRequest) -> SearchResponse:
    """Search DuckDuckGo specifically"""
    request.engine = SearchEngine.DUCKDUCKGO
    return await search(request)


@router.post(
    "/news",
    response_model=SearchResponse,
    summary="News Search",
    description="Search news articles across engines",
)
async def news_search(request: SearchRequest) -> SearchResponse:
    """Search news articles"""
    request.vertical = SearchVertical.NEWS
    return await search(request)


@router.post(
    "/images",
    response_model=SearchResponse,
    summary="Image Search",
    description="Search images across engines",
)
async def image_search(request: SearchRequest) -> SearchResponse:
    """Search images"""
    request.vertical = SearchVertical.IMAGES
    return await search(request)


@router.post(
    "/videos",
    response_model=SearchResponse,
    summary="Video Search",
    description="Search videos across engines",
)
async def video_search(request: SearchRequest) -> SearchResponse:
    """Search videos"""
    request.vertical = SearchVertical.VIDEOS
    return await search(request)
