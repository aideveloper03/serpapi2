"""
OmniScrape Engine - Base Search Engine
Abstract base class for all search engine parsers
"""

import re
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse, parse_qs
from bs4 import BeautifulSoup

from models import SearchResult, SearchVertical
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class ParseResult:
    """Result of parsing a search results page"""
    results: List[SearchResult]
    total_results: Optional[int] = None
    next_page_url: Optional[str] = None
    has_captcha: bool = False
    is_blocked: bool = False
    error: Optional[str] = None


class BaseSearchEngine(ABC):
    """
    Abstract base class for search engine scrapers.
    Each engine must implement specific parsing logic.
    """
    
    # Engine identifier
    ENGINE_NAME: str = "base"
    
    # Base URLs
    BASE_URL: str = ""
    SEARCH_PATH: str = ""
    NEWS_PATH: str = ""
    IMAGES_PATH: str = ""
    VIDEOS_PATH: str = ""
    
    # Rate limiting
    DEFAULT_DELAY: float = 1.0
    
    # Common selectors for CAPTCHA detection
    CAPTCHA_INDICATORS = [
        "captcha",
        "recaptcha",
        "g-recaptcha",
        "challenge",
        "unusual traffic",
        "automated queries",
        "robot",
        "not a robot",
        "verify you are human",
        "access denied",
        "blocked",
    ]
    
    def __init__(self, delay: Optional[float] = None):
        self.delay = delay or self.DEFAULT_DELAY
        self._last_request_time = 0.0
    
    @abstractmethod
    def build_search_url(
        self,
        query: str,
        vertical: SearchVertical,
        page: int = 1,
        num_results: int = 10,
        country: Optional[str] = None,
        language: Optional[str] = None,
        time_range: Optional[str] = None,
        safe_search: bool = True,
    ) -> str:
        """Build the search URL for this engine"""
        pass
    
    @abstractmethod
    def parse_results(
        self,
        html: str,
        vertical: SearchVertical,
    ) -> ParseResult:
        """Parse search results from HTML"""
        pass
    
    def detect_captcha(self, html: str) -> bool:
        """Detect if the page contains a CAPTCHA challenge"""
        html_lower = html.lower()
        
        for indicator in self.CAPTCHA_INDICATORS:
            if indicator in html_lower:
                return True
        
        return False
    
    def detect_block(self, html: str, status_code: int) -> bool:
        """Detect if the request was blocked"""
        if status_code in [403, 429, 503]:
            return True
        
        block_indicators = [
            "access denied",
            "blocked",
            "forbidden",
            "too many requests",
            "rate limit",
        ]
        
        html_lower = html.lower()
        return any(indicator in html_lower for indicator in block_indicators)
    
    def extract_total_results(self, html: str) -> Optional[int]:
        """Extract total results count from HTML"""
        # Common patterns
        patterns = [
            r'About ([\d,]+) results',
            r'([\d,]+) results',
            r'of about ([\d,]+)',
            r'([\d,]+) matches',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1).replace(',', ''))
                except ValueError:
                    pass
        
        return None
    
    def clean_url(self, url: str) -> str:
        """Clean and extract the actual URL from tracking URLs"""
        if not url:
            return ""
        
        # Handle Google redirect URLs
        if '/url?' in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if 'q' in params:
                return params['q'][0]
            if 'url' in params:
                return params['url'][0]
        
        # Handle Bing redirect URLs
        if 'bing.com/ck/' in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if 'u' in params:
                # Bing uses base64 encoding
                import base64
                try:
                    decoded = base64.b64decode(params['u'][0][2:]).decode('utf-8')
                    return decoded
                except:
                    pass
        
        return url
    
    def clean_text(self, text: Optional[str]) -> str:
        """Clean extracted text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common noise
        noise_patterns = [
            r'^\d+ days? ago\s*[-–]\s*',
            r'^\d+ hours? ago\s*[-–]\s*',
            r'^\d+ minutes? ago\s*[-–]\s*',
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text)
        
        return text
    
    def extract_date(self, text: str) -> Optional[str]:
        """Extract date from text"""
        patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
            r'(\w+ \d{1,2}, \d{4})',
            r'(\d{1,2} \w+ \d{4})',
            r'(\d+ (?:days?|hours?|minutes?|weeks?|months?|years?) ago)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    async def wait_for_rate_limit(self) -> None:
        """Wait if necessary for rate limiting"""
        import asyncio
        
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            await asyncio.sleep(self.delay - elapsed)
        
        self._last_request_time = time.time()
    
    def _soup(self, html: str) -> BeautifulSoup:
        """Create BeautifulSoup instance"""
        return BeautifulSoup(html, 'lxml')
