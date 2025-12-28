"""
OmniScrape Engine - Crawl API Endpoints
Endpoints for deep web crawling and content extraction
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from models import (
    CrawlRequest,
    CrawlResponse,
    CrawlerMode,
    ErrorResponse,
)
from core.crawlers import deep_scraper
from utils import get_logger, generate_trace_id

logger = get_logger(__name__)

router = APIRouter(prefix="/crawl", tags=["Crawl"])


@router.post(
    "",
    response_model=CrawlResponse,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Crawl Website",
    description="""
    Crawl a website and extract structured content.
    
    **Features:**
    - Deep crawling with configurable depth
    - Automatic content categorization
    - Contact information extraction
    - Metadata and Schema.org parsing
    - Multiple crawler modes for different needs
    
    **Crawler Modes:**
    - `simple`: Single page extraction
    - `deep`: Follow links up to specified depth
    - `stealth`: Use headless browser with anti-detection
    - `ghostnet`: Use GhostNet Protocol for maximum stealth
    
    **Extracted Data:**
    - Main content and article text
    - Emails, phones, and social links
    - OpenGraph and Twitter Card metadata
    - Schema.org structured data
    """,
)
async def crawl(request: CrawlRequest) -> CrawlResponse:
    """Crawl a website with content extraction"""
    trace_id = generate_trace_id()
    
    logger.info(
        "crawl_api_request",
        url=request.url,
        depth=request.depth,
        mode=request.crawler_mode.value,
        trace_id=trace_id,
    )
    
    try:
        response = await deep_scraper.crawl(request, trace_id)
        return response
        
    except Exception as e:
        logger.error(
            "crawl_api_error",
            url=request.url,
            error=str(e),
            trace_id=trace_id,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e),
                "error_code": "CRAWL_ERROR",
                "trace_id": trace_id,
            },
        )


@router.get(
    "",
    response_model=CrawlResponse,
    summary="Quick Crawl",
    description="Simplified GET endpoint for quick crawls",
)
async def quick_crawl(
    url: str = Query(..., description="URL to crawl"),
    depth: int = Query(default=1, ge=1, le=5, description="Crawl depth"),
    max_pages: int = Query(default=10, ge=1, le=100, description="Maximum pages"),
    mode: CrawlerMode = Query(default=CrawlerMode.SIMPLE, description="Crawler mode"),
    extract_content: bool = Query(default=True, description="Extract main content"),
    extract_contacts: bool = Query(default=True, description="Extract contacts"),
    extract_metadata: bool = Query(default=True, description="Extract metadata"),
    wait_for_js: bool = Query(default=False, description="Wait for JavaScript"),
) -> CrawlResponse:
    """Quick crawl via GET parameters"""
    request = CrawlRequest(
        url=url,
        depth=depth,
        max_pages=max_pages,
        crawler_mode=mode,
        extract_content=extract_content,
        extract_contacts=extract_contacts,
        extract_metadata=extract_metadata,
        wait_for_js=wait_for_js,
    )
    return await crawl(request)


@router.post(
    "/stealth",
    response_model=CrawlResponse,
    summary="Stealth Crawl",
    description="Crawl using stealth browser with anti-detection",
)
async def stealth_crawl(request: CrawlRequest) -> CrawlResponse:
    """Crawl using stealth browser"""
    request.crawler_mode = CrawlerMode.STEALTH
    return await crawl(request)


@router.post(
    "/ghostnet",
    response_model=CrawlResponse,
    summary="GhostNet Crawl",
    description="Crawl using the innovative GhostNet Protocol for maximum stealth",
)
async def ghostnet_crawl(request: CrawlRequest) -> CrawlResponse:
    """Crawl using GhostNet Protocol"""
    request.crawler_mode = CrawlerMode.GHOSTNET
    return await crawl(request)


@router.post(
    "/deep",
    response_model=CrawlResponse,
    summary="Deep Crawl",
    description="Deep crawl following links to specified depth",
)
async def deep_crawl(request: CrawlRequest) -> CrawlResponse:
    """Deep crawl with link following"""
    request.crawler_mode = CrawlerMode.DEEP
    if request.depth < 2:
        request.depth = 2
    return await crawl(request)


@router.post(
    "/single",
    response_model=CrawlResponse,
    summary="Single Page Crawl",
    description="Crawl a single page with full extraction",
)
async def single_page_crawl(request: CrawlRequest) -> CrawlResponse:
    """Crawl single page only"""
    request.depth = 1
    request.max_pages = 1
    return await crawl(request)
