"""
OmniScrape Engine - Search Orchestrator
Manages search execution with cascading fallback between engines
"""

import asyncio
import time
from typing import Optional, List, Dict, Any, Tuple, Type
from dataclasses import dataclass

from models import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchEngine,
    SearchVertical,
)
from config import settings
from utils import get_logger, generate_trace_id
from services import network_client, proxy_manager

from .base import BaseSearchEngine, ParseResult
from .google import GoogleSearchEngine
from .bing import BingSearchEngine
from .duckduckgo import DuckDuckGoSearchEngine
from .yahoo import YahooSearchEngine
from .yandex import YandexSearchEngine

logger = get_logger(__name__)


@dataclass
class EngineResult:
    """Result from a single engine attempt"""
    engine: str
    success: bool
    results: List[SearchResult]
    total_results: Optional[int]
    error: Optional[str]
    latency_ms: float
    used_fallback: bool = False


class SearchOrchestrator:
    """
    Orchestrates search requests across multiple engines with:
    - Cascading fallback when engines fail or return no results
    - Automatic CAPTCHA/block detection
    - Headless browser mode as last resort
    - Google-search-python fallback
    - Zero-results guard
    """
    
    # Engine classes in fallback order
    ENGINE_CLASSES: Dict[SearchEngine, Type[BaseSearchEngine]] = {
        SearchEngine.GOOGLE: GoogleSearchEngine,
        SearchEngine.DUCKDUCKGO: DuckDuckGoSearchEngine,
        SearchEngine.BING: BingSearchEngine,
        SearchEngine.YAHOO: YahooSearchEngine,
        SearchEngine.YANDEX: YandexSearchEngine,
    }
    
    # Default fallback chain
    DEFAULT_FALLBACK_CHAIN = [
        SearchEngine.GOOGLE,
        SearchEngine.DUCKDUCKGO,
        SearchEngine.BING,
        SearchEngine.YAHOO,
        SearchEngine.YANDEX,
    ]
    
    def __init__(self):
        self._engines: Dict[SearchEngine, BaseSearchEngine] = {}
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_serp_scrapes)
        self._initialize_engines()
    
    def _initialize_engines(self) -> None:
        """Initialize all search engine instances"""
        for engine_type, engine_class in self.ENGINE_CLASSES.items():
            self._engines[engine_type] = engine_class()
    
    async def search(
        self,
        request: SearchRequest,
        trace_id: Optional[str] = None,
    ) -> SearchResponse:
        """
        Execute a search request with automatic fallback.
        
        Zero-results guarantee: Will try multiple engines, regex fallback,
        and headless browser before returning empty results.
        """
        trace_id = trace_id or generate_trace_id()
        start_time = time.perf_counter()
        
        logger.info(
            "search_start",
            query=request.query,
            engine=request.engine.value,
            vertical=request.vertical.value,
            trace_id=trace_id,
        )
        
        # Determine which engines to try
        if request.engine == SearchEngine.AUTO:
            engines_to_try = self.DEFAULT_FALLBACK_CHAIN.copy()
        else:
            # Start with requested engine, then fallback chain
            engines_to_try = [request.engine]
            for engine in self.DEFAULT_FALLBACK_CHAIN:
                if engine != request.engine and engine not in engines_to_try:
                    engines_to_try.append(engine)
        
        results: List[SearchResult] = []
        total_results: Optional[int] = None
        fallback_chain: List[str] = []
        engine_used: str = ""
        
        async with self._semaphore:
            for engine_type in engines_to_try:
                engine = self._engines.get(engine_type)
                if not engine:
                    continue
                
                fallback_chain.append(engine_type.value)
                
                try:
                    # Try standard HTTP scraping
                    engine_result = await self._try_engine(
                        engine=engine,
                        request=request,
                        use_browser=False,
                    )
                    
                    if engine_result.success and engine_result.results:
                        results = engine_result.results
                        total_results = engine_result.total_results
                        engine_used = engine_result.engine
                        
                        logger.info(
                            "search_engine_success",
                            engine=engine_type.value,
                            results_count=len(results),
                            trace_id=trace_id,
                        )
                        break
                    
                    # If CAPTCHA/blocked and browser mode allowed, try browser
                    if request.force_browser or (
                        engine_result.error and 
                        ("captcha" in engine_result.error.lower() or 
                         "blocked" in engine_result.error.lower())
                    ):
                        logger.info(
                            "search_trying_browser",
                            engine=engine_type.value,
                            trace_id=trace_id,
                        )
                        
                        browser_result = await self._try_engine(
                            engine=engine,
                            request=request,
                            use_browser=True,
                        )
                        
                        if browser_result.success and browser_result.results:
                            results = browser_result.results
                            total_results = browser_result.total_results
                            engine_used = f"{browser_result.engine}_browser"
                            break
                    
                except Exception as e:
                    logger.warning(
                        "search_engine_error",
                        engine=engine_type.value,
                        error=str(e),
                        trace_id=trace_id,
                    )
                    continue
            
            # Last resort: google-search-python library
            if not results and request.vertical == SearchVertical.ALL:
                try:
                    results = await self._googlesearch_fallback(
                        query=request.query,
                        num_results=request.num_results,
                    )
                    if results:
                        engine_used = "googlesearch_library"
                        fallback_chain.append("googlesearch_library")
                        
                        logger.info(
                            "search_googlesearch_fallback_success",
                            results_count=len(results),
                            trace_id=trace_id,
                        )
                except Exception as e:
                    logger.warning(
                        "search_googlesearch_fallback_error",
                        error=str(e),
                        trace_id=trace_id,
                    )
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        response = SearchResponse(
            success=len(results) > 0,
            query=request.query,
            engine=engine_used or "none",
            vertical=request.vertical.value,
            total_results=total_results,
            results=results[:request.num_results],
            fallback_used=len(fallback_chain) > 1,
            fallback_chain=fallback_chain,
            execution_time_ms=round(execution_time, 2),
            trace_id=trace_id,
            cached=False,
        )
        
        logger.info(
            "search_complete",
            success=response.success,
            results_count=len(response.results),
            engine_used=engine_used,
            fallback_count=len(fallback_chain),
            execution_time_ms=response.execution_time_ms,
            trace_id=trace_id,
        )
        
        return response
    
    async def _try_engine(
        self,
        engine: BaseSearchEngine,
        request: SearchRequest,
        use_browser: bool = False,
    ) -> EngineResult:
        """Try a single engine"""
        start_time = time.perf_counter()
        
        try:
            # Build search URL
            url = engine.build_search_url(
                query=request.query,
                vertical=request.vertical,
                page=request.page,
                num_results=request.num_results,
                country=request.country,
                language=request.language,
                time_range=request.time_range,
                safe_search=request.safe_search,
            )
            
            # Wait for rate limiting
            await engine.wait_for_rate_limit()
            
            # Fetch page
            if use_browser:
                html = await self._fetch_with_browser(url)
            else:
                status, html, headers = await network_client.get(
                    url=url,
                    use_curl=True,
                    timeout=settings.request_timeout,
                )
                
                if status != 200:
                    return EngineResult(
                        engine=engine.ENGINE_NAME,
                        success=False,
                        results=[],
                        total_results=None,
                        error=f"HTTP {status}",
                        latency_ms=(time.perf_counter() - start_time) * 1000,
                    )
            
            # Parse results
            parse_result = engine.parse_results(html, request.vertical)
            
            latency = (time.perf_counter() - start_time) * 1000
            
            if parse_result.has_captcha:
                return EngineResult(
                    engine=engine.ENGINE_NAME,
                    success=False,
                    results=[],
                    total_results=None,
                    error="CAPTCHA detected",
                    latency_ms=latency,
                )
            
            if parse_result.is_blocked:
                return EngineResult(
                    engine=engine.ENGINE_NAME,
                    success=False,
                    results=[],
                    total_results=None,
                    error="Request blocked",
                    latency_ms=latency,
                )
            
            return EngineResult(
                engine=engine.ENGINE_NAME,
                success=len(parse_result.results) > 0,
                results=parse_result.results,
                total_results=parse_result.total_results,
                error=parse_result.error,
                latency_ms=latency,
            )
            
        except Exception as e:
            return EngineResult(
                engine=engine.ENGINE_NAME,
                success=False,
                results=[],
                total_results=None,
                error=str(e),
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )
    
    async def _fetch_with_browser(self, url: str) -> str:
        """Fetch page using headless browser with stealth"""
        try:
            from core.crawlers.stealth_browser import StealthBrowser
            
            async with StealthBrowser() as browser:
                html = await browser.fetch_page(url)
                return html
                
        except ImportError:
            # Fallback to basic playwright
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()
                
                await page.goto(url, wait_until="networkidle", timeout=30000)
                html = await page.content()
                
                await browser.close()
                return html
    
    async def _googlesearch_fallback(
        self,
        query: str,
        num_results: int = 10,
    ) -> List[SearchResult]:
        """Use google-search-python as last resort fallback"""
        try:
            from googlesearch import search
            
            results = []
            position = 0
            
            # Run in thread pool since it's synchronous
            loop = asyncio.get_event_loop()
            urls = await loop.run_in_executor(
                None,
                lambda: list(search(query, num=num_results, stop=num_results, pause=2.0))
            )
            
            for url in urls:
                position += 1
                from urllib.parse import urlparse
                
                results.append(SearchResult(
                    position=position,
                    title=urlparse(url).netloc,
                    url=url,
                    source="googlesearch_library",
                ))
            
            return results
            
        except Exception as e:
            logger.error("googlesearch_fallback_error", error=str(e))
            return []


# Singleton instance
search_orchestrator = SearchOrchestrator()
