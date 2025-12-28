"""
OmniScrape Engine - Deep Web Scraper
Comprehensive web scraper with content categorization and extraction
"""

import asyncio
import time
import random
from typing import Optional, List, Dict, Set, Tuple
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass, field
from collections import deque
from bs4 import BeautifulSoup

from models import (
    CrawlRequest,
    CrawlResponse,
    PageData,
    ExtractedContent,
    ExtractedContacts,
    ExtractedMetadata,
    CrawlerMode,
)
from config import settings
from utils import get_logger, generate_trace_id
from services import network_client, proxy_manager
from core.parsers.content_extractor import ContentExtractor
from core.parsers.contact_extractor import ContactExtractor
from core.parsers.metadata_extractor import MetadataExtractor

logger = get_logger(__name__)


@dataclass
class CrawlTask:
    """A single page to crawl"""
    url: str
    depth: int
    parent_url: Optional[str] = None


@dataclass
class CrawlState:
    """State of an ongoing crawl"""
    visited_urls: Set[str] = field(default_factory=set)
    pending_urls: deque = field(default_factory=deque)
    pages: List[PageData] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    max_depth_reached: int = 0


class DeepScraper:
    """
    Deep web scraper with comprehensive content extraction:
    - Automatic content categorization
    - Contact information extraction
    - Metadata and Schema.org parsing
    - Link following with depth control
    - Respectful crawling with delays
    """
    
    def __init__(self):
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_deep_scrapes)
    
    async def crawl(
        self,
        request: CrawlRequest,
        trace_id: Optional[str] = None,
    ) -> CrawlResponse:
        """
        Crawl a website starting from the given URL.
        
        Supports multiple modes:
        - SIMPLE: Single page extraction
        - DEEP: Follow links up to specified depth
        - STEALTH: Use headless browser with anti-detection
        - GHOSTNET: Use custom GhostNet crawler
        """
        trace_id = trace_id or generate_trace_id()
        start_time = time.perf_counter()
        
        logger.info(
            "crawl_start",
            url=request.url,
            depth=request.depth,
            mode=request.crawler_mode.value,
            trace_id=trace_id,
        )
        
        state = CrawlState()
        base_domain = urlparse(request.url).netloc
        
        # Add initial URL
        state.pending_urls.append(CrawlTask(url=request.url, depth=0))
        
        async with self._semaphore:
            while state.pending_urls and len(state.pages) < request.max_pages:
                # Get next task
                task = state.pending_urls.popleft()
                
                # Skip if already visited
                if task.url in state.visited_urls:
                    continue
                
                # Skip if depth exceeded
                if task.depth > request.depth:
                    continue
                
                state.visited_urls.add(task.url)
                
                try:
                    # Fetch and process page
                    page_data = await self._process_page(
                        url=task.url,
                        request=request,
                        trace_id=trace_id,
                    )
                    
                    if page_data:
                        state.pages.append(page_data)
                        state.max_depth_reached = max(state.max_depth_reached, task.depth)
                        
                        # Extract and queue links if not at max depth
                        if task.depth < request.depth:
                            new_links = self._extract_links(
                                page_data=page_data,
                                base_domain=base_domain,
                                follow_external=request.follow_external,
                            )
                            
                            for link in new_links:
                                if link not in state.visited_urls:
                                    state.pending_urls.append(
                                        CrawlTask(
                                            url=link,
                                            depth=task.depth + 1,
                                            parent_url=task.url,
                                        )
                                    )
                        
                        logger.debug(
                            "page_crawled",
                            url=task.url,
                            depth=task.depth,
                            trace_id=trace_id,
                        )
                    
                    # Respectful delay between requests
                    delay = random.uniform(
                        settings.crawl_delay_min,
                        settings.crawl_delay_max,
                    )
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    error_msg = f"Error crawling {task.url}: {str(e)}"
                    state.errors.append(error_msg)
                    logger.warning(
                        "page_crawl_error",
                        url=task.url,
                        error=str(e),
                        trace_id=trace_id,
                    )
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        response = CrawlResponse(
            success=len(state.pages) > 0,
            url=request.url,
            pages_crawled=len(state.pages),
            depth_reached=state.max_depth_reached,
            pages=state.pages,
            execution_time_ms=round(execution_time, 2),
            trace_id=trace_id,
            errors=state.errors,
        )
        
        logger.info(
            "crawl_complete",
            url=request.url,
            pages_crawled=response.pages_crawled,
            depth_reached=response.depth_reached,
            execution_time_ms=response.execution_time_ms,
            errors_count=len(state.errors),
            trace_id=trace_id,
        )
        
        return response
    
    async def _process_page(
        self,
        url: str,
        request: CrawlRequest,
        trace_id: str,
    ) -> Optional[PageData]:
        """Fetch and process a single page"""
        
        # Choose fetch method based on mode
        if request.crawler_mode == CrawlerMode.STEALTH:
            html, status, final_url = await self._fetch_with_stealth(
                url=url,
                request=request,
            )
        elif request.crawler_mode == CrawlerMode.GHOSTNET:
            html, status, final_url = await self._fetch_with_ghostnet(
                url=url,
                request=request,
            )
        elif request.wait_for_js:
            html, status, final_url = await self._fetch_with_browser(
                url=url,
                request=request,
            )
        else:
            html, status, final_url = await self._fetch_with_http(
                url=url,
                request=request,
            )
        
        if not html or status >= 400:
            return None
        
        # Extract content
        content = None
        contacts = None
        metadata = None
        
        if request.extract_content:
            content = ContentExtractor(html, url).extract()
        
        if request.extract_contacts:
            contacts = ContactExtractor(html, url).extract()
        
        if request.extract_metadata:
            metadata = MetadataExtractor(html, url).extract()
        
        # Extract links
        soup = BeautifulSoup(html, 'lxml')
        all_links = self._get_all_links(soup, url)
        internal_links, external_links = self._categorize_links(all_links, url)
        
        return PageData(
            url=url,
            status_code=status,
            final_url=final_url if final_url != url else None,
            content=content,
            contacts=contacts,
            metadata=metadata,
            links=list(all_links)[:100],  # Limit links
            internal_links=internal_links[:50],
            external_links=external_links[:50],
            raw_html=html if len(html) < 500000 else None,  # Don't store huge pages
        )
    
    async def _fetch_with_http(
        self,
        url: str,
        request: CrawlRequest,
    ) -> Tuple[Optional[str], int, str]:
        """Fetch page using HTTP client"""
        try:
            headers = request.custom_headers or {}
            
            status, html, response_headers = await network_client.get(
                url=url,
                headers=headers,
                timeout=settings.request_timeout,
                use_curl=True,
            )
            
            return html, status, url
            
        except Exception as e:
            logger.error("http_fetch_error", url=url, error=str(e))
            return None, 0, url
    
    async def _fetch_with_browser(
        self,
        url: str,
        request: CrawlRequest,
    ) -> Tuple[Optional[str], int, str]:
        """Fetch page using headless browser"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=settings.headless_mode)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                
                if request.cookies:
                    await context.add_cookies([
                        {"name": k, "value": v, "domain": urlparse(url).netloc}
                        for k, v in request.cookies.items()
                    ])
                
                page = await context.new_page()
                
                response = await page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=settings.browser_timeout,
                )
                
                if request.js_wait_time > 0:
                    await asyncio.sleep(request.js_wait_time / 1000)
                
                html = await page.content()
                final_url = page.url
                status = response.status if response else 200
                
                await browser.close()
                
                return html, status, final_url
                
        except Exception as e:
            logger.error("browser_fetch_error", url=url, error=str(e))
            return None, 0, url
    
    async def _fetch_with_stealth(
        self,
        url: str,
        request: CrawlRequest,
    ) -> Tuple[Optional[str], int, str]:
        """Fetch page using stealth browser"""
        try:
            from core.crawlers.stealth_browser import StealthBrowser
            
            async with StealthBrowser() as browser:
                html, final_url = await browser.fetch_page_with_url(url)
                return html, 200, final_url
                
        except Exception as e:
            logger.error("stealth_fetch_error", url=url, error=str(e))
            # Fall back to regular browser
            return await self._fetch_with_browser(url, request)
    
    async def _fetch_with_ghostnet(
        self,
        url: str,
        request: CrawlRequest,
    ) -> Tuple[Optional[str], int, str]:
        """Fetch page using GhostNet crawler"""
        try:
            from core.crawlers.ghostnet import GhostNetCrawler
            
            async with GhostNetCrawler() as crawler:
                result = await crawler.fetch(url)
                return result.html, result.status_code, result.final_url
                
        except Exception as e:
            logger.error("ghostnet_fetch_error", url=url, error=str(e))
            # Fall back to stealth browser
            return await self._fetch_with_stealth(url, request)
    
    def _get_all_links(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """Extract all links from a page"""
        links = set()
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Skip non-http links
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            
            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            
            # Normalize URL
            parsed = urlparse(full_url)
            if parsed.scheme in ('http', 'https'):
                # Remove fragment
                normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if parsed.query:
                    normalized += f"?{parsed.query}"
                links.add(normalized)
        
        return links
    
    def _categorize_links(
        self,
        links: Set[str],
        base_url: str,
    ) -> Tuple[List[str], List[str]]:
        """Categorize links into internal and external"""
        base_domain = urlparse(base_url).netloc
        internal = []
        external = []
        
        for link in links:
            parsed = urlparse(link)
            if parsed.netloc == base_domain or parsed.netloc.endswith('.' + base_domain):
                internal.append(link)
            else:
                external.append(link)
        
        return sorted(internal), sorted(external)
    
    def _extract_links(
        self,
        page_data: PageData,
        base_domain: str,
        follow_external: bool,
    ) -> List[str]:
        """Extract links to follow from a page"""
        if follow_external:
            return page_data.internal_links + page_data.external_links
        return page_data.internal_links


# Singleton instance
deep_scraper = DeepScraper()
