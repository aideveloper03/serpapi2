"""
OmniScrape Engine - Data Mining API Endpoints
Endpoints for bulk data extraction and mining
"""

import asyncio
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from models import (
    DataMineRequest,
    DataMineResponse,
    MinedData,
    CrawlRequest,
    CrawlerMode,
    ErrorResponse,
)
from core.crawlers import deep_scraper
from utils import get_logger, generate_trace_id
from config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/mine", tags=["Data Mining"])


@router.post(
    "",
    response_model=DataMineResponse,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Mine Data from URLs",
    description="""
    Extract structured data from multiple URLs.
    
    **Extracted Data:**
    - Email addresses
    - Phone numbers
    - Social media links
    - Physical addresses
    - Company information (from Schema.org)
    
    **Processing:**
    - Parallel processing for speed
    - Automatic deduplication
    - Error handling per URL
    """,
)
async def mine_data(request: DataMineRequest) -> DataMineResponse:
    """Mine data from multiple URLs"""
    trace_id = generate_trace_id()
    
    logger.info(
        "mine_api_request",
        urls_count=len(request.urls),
        parallel=request.parallel,
        trace_id=trace_id,
    )
    
    try:
        import time
        start_time = time.perf_counter()
        
        results: List[MinedData] = []
        errors: List[str] = []
        
        if request.parallel:
            # Process URLs in parallel with concurrency limit
            semaphore = asyncio.Semaphore(settings.max_concurrent_deep_scrapes)
            
            async def process_url(url: str) -> Optional[MinedData]:
                async with semaphore:
                    return await _mine_single_url(url, request)
            
            tasks = [process_url(url) for url in request.urls]
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, result in zip(request.urls, task_results):
                if isinstance(result, Exception):
                    errors.append(f"{url}: {str(result)}")
                elif result:
                    results.append(result)
        else:
            # Process URLs sequentially
            for url in request.urls:
                try:
                    result = await _mine_single_url(url, request)
                    if result:
                        results.append(result)
                except Exception as e:
                    errors.append(f"{url}: {str(e)}")
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        return DataMineResponse(
            success=len(results) > 0,
            urls_processed=len(results),
            results=results,
            execution_time_ms=round(execution_time, 2),
            trace_id=trace_id,
            errors=errors,
        )
        
    except Exception as e:
        logger.error(
            "mine_api_error",
            error=str(e),
            trace_id=trace_id,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e),
                "error_code": "MINE_ERROR",
                "trace_id": trace_id,
            },
        )


async def _mine_single_url(url: str, request: DataMineRequest) -> Optional[MinedData]:
    """Mine data from a single URL"""
    crawl_request = CrawlRequest(
        url=url,
        depth=1,
        max_pages=1,
        crawler_mode=CrawlerMode.SIMPLE,
        extract_content=False,
        extract_contacts=True,
        extract_metadata=True,
    )
    
    response = await deep_scraper.crawl(crawl_request)
    
    if not response.pages:
        return None
    
    page = response.pages[0]
    
    # Aggregate mined data
    mined = MinedData(url=url)
    
    if page.contacts:
        if request.extract_emails:
            mined.emails = page.contacts.emails
        if request.extract_phones:
            mined.phones = page.contacts.phones
        if request.extract_social:
            mined.social_links = page.contacts.social_links
        if request.extract_addresses:
            mined.addresses = page.contacts.addresses
    
    if request.extract_company_info and page.metadata:
        # Extract company info from structured data
        company_info = {}
        for sd in page.metadata.structured_data:
            if isinstance(sd, dict):
                sd_type = sd.get('@type', '')
                if sd_type in ['Organization', 'LocalBusiness', 'Corporation']:
                    company_info.update({
                        'name': sd.get('name'),
                        'description': sd.get('description'),
                        'url': sd.get('url'),
                        'logo': sd.get('logo'),
                        'telephone': sd.get('telephone'),
                        'email': sd.get('email'),
                        'address': sd.get('address'),
                    })
        if company_info:
            mined.company_info = {k: v for k, v in company_info.items() if v}
    
    return mined


@router.get(
    "/emails",
    response_model=DataMineResponse,
    summary="Extract Emails",
    description="Extract email addresses from URLs",
)
async def extract_emails(
    urls: List[str] = Query(..., description="URLs to extract emails from"),
) -> DataMineResponse:
    """Extract emails from URLs"""
    request = DataMineRequest(
        urls=urls,
        extract_emails=True,
        extract_phones=False,
        extract_social=False,
        extract_addresses=False,
        extract_company_info=False,
    )
    return await mine_data(request)


@router.get(
    "/contacts",
    response_model=DataMineResponse,
    summary="Extract All Contacts",
    description="Extract all contact information from URLs",
)
async def extract_contacts(
    urls: List[str] = Query(..., description="URLs to extract contacts from"),
) -> DataMineResponse:
    """Extract all contacts from URLs"""
    request = DataMineRequest(
        urls=urls,
        extract_emails=True,
        extract_phones=True,
        extract_social=True,
        extract_addresses=True,
        extract_company_info=True,
    )
    return await mine_data(request)


@router.post(
    "/batch",
    response_model=DataMineResponse,
    summary="Batch Data Mining",
    description="Mine data from a large batch of URLs",
)
async def batch_mine(
    urls: List[str],
    extract_emails: bool = True,
    extract_phones: bool = True,
    extract_social: bool = True,
) -> DataMineResponse:
    """Batch mine data from URLs"""
    request = DataMineRequest(
        urls=urls[:100],  # Limit to 100 URLs
        extract_emails=extract_emails,
        extract_phones=extract_phones,
        extract_social=extract_social,
        parallel=True,
    )
    return await mine_data(request)
