"""
OmniScrape Engine - Yahoo Search Parser
Yahoo search scraper (powered by Bing backend)
"""

import re
from typing import Optional, List
from urllib.parse import urlencode, urlparse, unquote, parse_qs
from bs4 import BeautifulSoup

from models import SearchResult, SearchVertical
from config import settings
from .base import BaseSearchEngine, ParseResult


class YahooSearchEngine(BaseSearchEngine):
    """
    Yahoo search engine parser.
    Yahoo uses Bing's backend but has its own result format.
    """
    
    ENGINE_NAME = "yahoo"
    BASE_URL = "https://search.yahoo.com"
    SEARCH_PATH = "/search"
    NEWS_PATH = "/news"
    IMAGES_PATH = "/images"
    VIDEOS_PATH = "/video"
    DEFAULT_DELAY = settings.yahoo_delay
    
    SELECTORS = {
        "result_container": [
            "div.dd.algo",
            "li.ov-a",
            "div.Sr",
        ],
        "title": [
            "h3.title a",
            "a.ac-algo",
            "h3 a",
        ],
        "link": [
            "h3.title a[href]",
            "a.ac-algo[href]",
        ],
        "description": [
            "div.compText",
            "p.lh-16",
            "div.dd span",
        ],
        "displayed_url": [
            "span.fz-ms",
            "span.url",
        ],
        "news_container": [
            "li.StreamItem",
            "div.NewsArticle",
        ],
        "image_container": [
            "li.ld",
            "div.img",
        ],
        "video_container": [
            "li.vr",
            "div.v",
        ],
    }
    
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
        """Build Yahoo search URL"""
        
        params = {
            "p": query,
            "n": num_results,
        }
        
        # Path based on vertical
        if vertical == SearchVertical.NEWS:
            path = f"{self.NEWS_PATH}/search"
        elif vertical == SearchVertical.IMAGES:
            path = f"{self.IMAGES_PATH}/search"
        elif vertical == SearchVertical.VIDEOS:
            path = f"{self.VIDEOS_PATH}/search"
        else:
            path = self.SEARCH_PATH
        
        # Pagination
        if page > 1:
            params["b"] = ((page - 1) * 10) + 1
        
        # Time range
        if time_range:
            time_map = {
                "d": "1d",
                "w": "1w",
                "m": "1m",
                "y": "1y",
            }
            if time_range in time_map:
                params["age"] = time_map[time_range]
        
        # Safe search
        params["vm"] = "r" if safe_search else "p"
        
        return f"{self.BASE_URL}{path}?{urlencode(params)}"
    
    def parse_results(
        self,
        html: str,
        vertical: SearchVertical,
    ) -> ParseResult:
        """Parse Yahoo search results"""
        
        if self.detect_captcha(html):
            return ParseResult(
                results=[],
                has_captcha=True,
                error="CAPTCHA detected",
            )
        
        if self.detect_block(html, 200):
            return ParseResult(
                results=[],
                is_blocked=True,
                error="Request blocked",
            )
        
        soup = self._soup(html)
        
        if vertical == SearchVertical.NEWS:
            results = self._parse_news_results(soup)
        elif vertical == SearchVertical.IMAGES:
            results = self._parse_image_results(soup, html)
        elif vertical == SearchVertical.VIDEOS:
            results = self._parse_video_results(soup)
        else:
            results = self._parse_organic_results(soup)
        
        if not results:
            results = self._regex_fallback(html, vertical)
        
        total_results = self.extract_total_results(html)
        
        return ParseResult(
            results=results,
            total_results=total_results,
        )
    
    def _decode_yahoo_url(self, url: str) -> str:
        """Decode Yahoo redirect URLs"""
        if not url:
            return ""
        
        # Yahoo uses RU parameter for redirect
        if 'yahoo.com' in url and '/RU=' in url:
            match = re.search(r'/RU=([^/]+)/', url)
            if match:
                return unquote(match.group(1))
        
        # Check for standard query parameter
        if '?' in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if 'u' in params:
                return params['u'][0]
        
        return url
    
    def _parse_organic_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse Yahoo organic results"""
        results = []
        position = 0
        seen_urls = set()
        
        # Find result containers
        containers = soup.select("div.dd.algo")
        if not containers:
            containers = soup.select("li.ov-a")
        if not containers:
            containers = soup.select("div[class*='algo']")
        
        for container in containers:
            try:
                # Title and link
                title_elem = container.select_one("h3.title a") or \
                            container.select_one("h3 a") or \
                            container.select_one("a.ac-algo")
                
                if not title_elem:
                    continue
                
                title = self.clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                url = self._decode_yahoo_url(url)
                
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                # Skip Yahoo internal
                if 'yahoo.com' in url and '/search' not in url:
                    pass  # Allow search results
                
                seen_urls.add(url)
                position += 1
                
                # Description
                desc_elem = container.select_one("div.compText") or \
                           container.select_one("p")
                description = self.clean_text(desc_elem.get_text()) if desc_elem else ""
                
                # Displayed URL
                url_elem = container.select_one("span.fz-ms") or \
                          container.select_one("span.url")
                displayed_url = self.clean_text(url_elem.get_text()) if url_elem else ""
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    description=description,
                    displayed_url=displayed_url,
                    source="yahoo",
                ))
                
            except Exception:
                continue
        
        return results
    
    def _parse_news_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse Yahoo News results"""
        results = []
        position = 0
        seen_urls = set()
        
        containers = soup.select("li.StreamItem")
        if not containers:
            containers = soup.select("div.NewsArticle")
        if not containers:
            containers = soup.select("article")
        
        for container in containers:
            try:
                link_elem = container.select_one("a[href]")
                if not link_elem:
                    continue
                
                url = self._decode_yahoo_url(link_elem.get('href', ''))
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Title
                title_elem = container.select_one("h3") or \
                            container.select_one("h4") or \
                            container.select_one("[data-test-locator='stream-item-title']")
                title = self.clean_text(title_elem.get_text()) if title_elem else ""
                
                if not title:
                    continue
                
                # Description
                desc_elem = container.select_one("p")
                description = self.clean_text(desc_elem.get_text()) if desc_elem else ""
                
                # Source
                source_elem = container.select_one("span[class*='provider']")
                source = self.clean_text(source_elem.get_text()) if source_elem else "yahoo_news"
                
                # Thumbnail
                img_elem = container.select_one("img")
                thumbnail = img_elem.get("src") if img_elem else None
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    description=description,
                    source=source,
                    thumbnail=thumbnail,
                ))
                
            except Exception:
                continue
        
        return results
    
    def _parse_image_results(self, soup: BeautifulSoup, html: str) -> List[SearchResult]:
        """Parse Yahoo Image results"""
        results = []
        position = 0
        seen_urls = set()
        
        containers = soup.select("li.ld")
        if not containers:
            containers = soup.select("li[data-pos]")
        
        for container in containers:
            try:
                # Try to get image data
                link_elem = container.select_one("a[href]")
                img_elem = container.select_one("img")
                
                if not img_elem:
                    continue
                
                # Get actual image URL
                url = img_elem.get('data-src') or img_elem.get('src', '')
                if not url.startswith('http'):
                    # Try to extract from link
                    if link_elem:
                        href = link_elem.get('href', '')
                        url = self._decode_yahoo_url(href)
                
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                title = img_elem.get('alt', f"Image {position}")
                
                results.append(SearchResult(
                    position=position,
                    title=self.clean_text(title),
                    url=url,
                    thumbnail=img_elem.get('src'),
                    source="yahoo_images",
                ))
                
            except Exception:
                continue
        
        return results
    
    def _parse_video_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse Yahoo Video results"""
        results = []
        position = 0
        seen_urls = set()
        
        containers = soup.select("li.vr")
        if not containers:
            containers = soup.select("div[class*='video']")
        
        for container in containers:
            try:
                link_elem = container.select_one("a[href]")
                if not link_elem:
                    continue
                
                url = self._decode_yahoo_url(link_elem.get('href', ''))
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Title
                title_elem = container.select_one("h3") or \
                            container.select_one("[title]")
                title = ""
                if title_elem:
                    title = title_elem.get('title', '') or title_elem.get_text()
                title = self.clean_text(title) or f"Video {position}"
                
                # Thumbnail
                img_elem = container.select_one("img")
                thumbnail = img_elem.get("src") if img_elem else None
                
                # Duration
                duration_elem = container.select_one("span.v-time")
                extra = {}
                if duration_elem:
                    extra["duration"] = self.clean_text(duration_elem.get_text())
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    thumbnail=thumbnail,
                    source="yahoo_videos",
                    extra=extra if extra else None,
                ))
                
            except Exception:
                continue
        
        return results
    
    def _regex_fallback(self, html: str, vertical: SearchVertical) -> List[SearchResult]:
        """Regex fallback for Yahoo"""
        results = []
        position = 0
        seen = set()
        
        # Find RU parameter URLs
        ru_matches = re.findall(r'/RU=([^/]+)/', html)
        
        for match in ru_matches:
            try:
                url = unquote(match)
                
                if not url.startswith('http') or url in seen:
                    continue
                
                if 'yahoo.com' in url:
                    continue
                
                seen.add(url)
                position += 1
                
                results.append(SearchResult(
                    position=position,
                    title=urlparse(url).netloc,
                    url=url,
                    source="yahoo_regex",
                ))
                
                if position >= 15:
                    break
                    
            except Exception:
                continue
        
        return results
