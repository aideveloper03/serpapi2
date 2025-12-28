"""
OmniScrape Engine - Pydantic Models
Request and Response schemas for the API
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, HttpUrl, field_validator


# Enums
class SearchEngine(str, Enum):
    """Supported search engines"""
    GOOGLE = "google"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    YAHOO = "yahoo"
    YANDEX = "yandex"
    AUTO = "auto"  # Automatic fallback


class SearchVertical(str, Enum):
    """Search verticals"""
    ALL = "all"
    NEWS = "news"
    IMAGES = "images"
    VIDEOS = "videos"


class ProxyType(str, Enum):
    """Proxy types"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class CrawlerMode(str, Enum):
    """Crawler operation modes"""
    SIMPLE = "simple"
    DEEP = "deep"
    STEALTH = "stealth"
    GHOSTNET = "ghostnet"


class ContentType(str, Enum):
    """Content types for extraction"""
    ARTICLE = "article"
    PRODUCT = "product"
    LISTING = "listing"
    FORUM = "forum"
    NEWS = "news"
    BLOG = "blog"
    UNKNOWN = "unknown"


# Request Models
class SearchRequest(BaseModel):
    """Search API request model"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    engine: SearchEngine = Field(default=SearchEngine.AUTO, description="Search engine to use")
    vertical: SearchVertical = Field(default=SearchVertical.ALL, description="Search vertical")
    num_results: int = Field(default=10, ge=1, le=100, description="Number of results")
    page: int = Field(default=1, ge=1, le=50, description="Page number")
    country: Optional[str] = Field(default=None, max_length=2, description="Country code (e.g., 'us')")
    language: Optional[str] = Field(default=None, max_length=5, description="Language code (e.g., 'en')")
    safe_search: bool = Field(default=True, description="Enable safe search")
    time_range: Optional[str] = Field(default=None, description="Time range filter (d=day, w=week, m=month, y=year)")
    use_proxy: bool = Field(default=True, description="Use proxy rotation")
    force_browser: bool = Field(default=False, description="Force headless browser mode")
    
    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.lower()
        return v
    
    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.lower()
        return v


class CrawlRequest(BaseModel):
    """Deep crawl API request model"""
    url: str = Field(..., description="URL to crawl")
    depth: int = Field(default=1, ge=1, le=5, description="Crawl depth")
    max_pages: int = Field(default=10, ge=1, le=100, description="Maximum pages to crawl")
    crawler_mode: CrawlerMode = Field(default=CrawlerMode.SIMPLE, description="Crawler mode")
    follow_external: bool = Field(default=False, description="Follow external links")
    extract_content: bool = Field(default=True, description="Extract main content")
    extract_contacts: bool = Field(default=True, description="Extract contact information")
    extract_metadata: bool = Field(default=True, description="Extract metadata")
    extract_schema: bool = Field(default=True, description="Extract Schema.org data")
    respect_robots: bool = Field(default=False, description="Respect robots.txt")
    use_proxy: bool = Field(default=True, description="Use proxy rotation")
    custom_headers: Optional[Dict[str, str]] = Field(default=None, description="Custom headers")
    cookies: Optional[Dict[str, str]] = Field(default=None, description="Cookies to send")
    wait_for_js: bool = Field(default=False, description="Wait for JavaScript rendering")
    js_wait_time: int = Field(default=2000, ge=0, le=30000, description="JS wait time in ms")


class DataMineRequest(BaseModel):
    """Data mining request model"""
    urls: List[str] = Field(..., min_length=1, max_length=100, description="URLs to mine")
    extract_emails: bool = Field(default=True)
    extract_phones: bool = Field(default=True)
    extract_social: bool = Field(default=True)
    extract_addresses: bool = Field(default=True)
    extract_company_info: bool = Field(default=True)
    parallel: bool = Field(default=True, description="Process URLs in parallel")


# Response Models
class SearchResult(BaseModel):
    """Individual search result"""
    position: int = Field(..., description="Result position")
    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    description: Optional[str] = Field(default=None, description="Result description/snippet")
    displayed_url: Optional[str] = Field(default=None, description="Displayed URL")
    date: Optional[str] = Field(default=None, description="Published date")
    thumbnail: Optional[str] = Field(default=None, description="Thumbnail URL")
    source: Optional[str] = Field(default=None, description="Source name")
    cached_url: Optional[str] = Field(default=None, description="Cached version URL")
    extra: Optional[Dict[str, Any]] = Field(default=None, description="Extra data")


class SearchResponse(BaseModel):
    """Search API response model"""
    success: bool = Field(..., description="Request success status")
    query: str = Field(..., description="Original query")
    engine: str = Field(..., description="Engine used")
    vertical: str = Field(..., description="Vertical searched")
    total_results: Optional[int] = Field(default=None, description="Total results estimate")
    results: List[SearchResult] = Field(default_factory=list, description="Search results")
    fallback_used: bool = Field(default=False, description="Whether fallback was used")
    fallback_chain: List[str] = Field(default_factory=list, description="Engines tried")
    execution_time_ms: float = Field(..., description="Execution time in ms")
    trace_id: str = Field(..., description="Request trace ID")
    cached: bool = Field(default=False, description="Whether result was cached")


class ExtractedContent(BaseModel):
    """Extracted content from a page"""
    title: Optional[str] = None
    text: Optional[str] = None
    summary: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    publish_date: Optional[str] = None
    content_type: ContentType = ContentType.UNKNOWN
    word_count: int = 0
    reading_time_minutes: int = 0
    language: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)


class ExtractedContacts(BaseModel):
    """Extracted contact information"""
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    social_links: Dict[str, List[str]] = Field(default_factory=dict)
    addresses: List[str] = Field(default_factory=list)


class ExtractedMetadata(BaseModel):
    """Extracted page metadata"""
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    canonical_url: Optional[str] = None
    og_data: Dict[str, str] = Field(default_factory=dict)
    twitter_data: Dict[str, str] = Field(default_factory=dict)
    structured_data: List[Dict[str, Any]] = Field(default_factory=list)
    favicon: Optional[str] = None
    language: Optional[str] = None
    charset: Optional[str] = None


class PageData(BaseModel):
    """Complete page data"""
    url: str
    status_code: int
    final_url: Optional[str] = None
    content: Optional[ExtractedContent] = None
    contacts: Optional[ExtractedContacts] = None
    metadata: Optional[ExtractedMetadata] = None
    links: List[str] = Field(default_factory=list)
    internal_links: List[str] = Field(default_factory=list)
    external_links: List[str] = Field(default_factory=list)
    raw_html: Optional[str] = None
    screenshot: Optional[str] = None
    crawled_at: datetime = Field(default_factory=datetime.utcnow)


class CrawlResponse(BaseModel):
    """Crawl API response model"""
    success: bool
    url: str
    pages_crawled: int
    depth_reached: int
    pages: List[PageData]
    execution_time_ms: float
    trace_id: str
    errors: List[str] = Field(default_factory=list)


class MinedData(BaseModel):
    """Mined data from multiple URLs"""
    url: str
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    social_links: Dict[str, List[str]] = Field(default_factory=dict)
    addresses: List[str] = Field(default_factory=list)
    company_info: Optional[Dict[str, Any]] = None


class DataMineResponse(BaseModel):
    """Data mining response model"""
    success: bool
    urls_processed: int
    results: List[MinedData]
    execution_time_ms: float
    trace_id: str
    errors: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    uptime_seconds: float
    redis_connected: bool
    proxy_pool_size: int
    active_requests: int


class ProxyInfo(BaseModel):
    """Proxy information"""
    url: str
    type: ProxyType
    country: Optional[str] = None
    latency_ms: Optional[float] = None
    success_rate: float = 1.0
    last_used: Optional[datetime] = None
    is_valid: bool = True


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    error_code: str
    trace_id: str
    details: Optional[Dict[str, Any]] = None
