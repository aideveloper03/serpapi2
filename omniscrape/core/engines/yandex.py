"""
OmniScrape Engine - Yandex Search Parser
Yandex search scraper - Russian search engine
"""

import re
import json
from typing import Optional, List
from urllib.parse import urlencode, urlparse
from bs4 import BeautifulSoup

from models import SearchResult, SearchVertical
from config import settings
from .base import BaseSearchEngine, ParseResult


class YandexSearchEngine(BaseSearchEngine):
    """
    Yandex search engine parser.
    Yandex has strong anti-bot measures.
    """
    
    ENGINE_NAME = "yandex"
    BASE_URL = "https://yandex.com"
    SEARCH_PATH = "/search/"
    NEWS_PATH = "/news/search"
    IMAGES_PATH = "/images/search"
    VIDEOS_PATH = "/video/search"
    DEFAULT_DELAY = settings.yandex_delay
    
    SELECTORS = {
        "result_container": [
            "li.serp-item",
            "div.organic",
            "div[data-cid]",
        ],
        "title": [
            "h2 a.OrganicTitle-Link",
            "a.Link",
            "h2 a",
        ],
        "link": [
            "h2 a[href]",
            "a.OrganicTitle-Link[href]",
        ],
        "description": [
            "div.OrganicText",
            "div.text-container",
            "span.OrganicTextContentSpan",
        ],
        "displayed_url": [
            "a.Link_theme_outer",
            "div.Path",
        ],
        "news_container": [
            "article.news-card",
            "div.story",
        ],
        "image_container": [
            "div.serp-item",
            "div.serp-item_type_image",
        ],
        "video_container": [
            "div.serp-item_type_video",
            "div.video-item",
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
        """Build Yandex search URL"""
        
        params = {
            "text": query,
        }
        
        # Path based on vertical
        if vertical == SearchVertical.NEWS:
            path = self.NEWS_PATH
        elif vertical == SearchVertical.IMAGES:
            path = self.IMAGES_PATH
        elif vertical == SearchVertical.VIDEOS:
            path = self.VIDEOS_PATH
        else:
            path = self.SEARCH_PATH
        
        # Pagination
        if page > 1:
            params["p"] = page - 1
        
        # Language/region
        if language:
            params["lang"] = language
        if country:
            params["lr"] = self._get_region_code(country)
        
        # Time range
        if time_range:
            time_map = {
                "d": "77",
                "w": "1",
                "m": "2",
                "y": "3",
            }
            if time_range in time_map:
                params["within"] = time_map[time_range]
        
        # Safe search (family filter)
        params["family"] = "yes" if safe_search else "no"
        
        return f"{self.BASE_URL}{path}?{urlencode(params)}"
    
    def _get_region_code(self, country: str) -> str:
        """Get Yandex region code from country code"""
        region_map = {
            "ru": "225",   # Russia
            "us": "84",    # USA
            "uk": "102",   # UK
            "de": "96",    # Germany
            "fr": "124",   # France
            "ua": "187",   # Ukraine
            "by": "149",   # Belarus
            "kz": "159",   # Kazakhstan
            "tr": "983",   # Turkey
        }
        return region_map.get(country.lower(), "225")
    
    def parse_results(
        self,
        html: str,
        vertical: SearchVertical,
    ) -> ParseResult:
        """Parse Yandex search results"""
        
        if self.detect_captcha(html):
            return ParseResult(
                results=[],
                has_captcha=True,
                error="CAPTCHA detected",
            )
        
        # Yandex uses SmartCaptcha
        if "showcaptcha" in html.lower() or "smartcaptcha" in html.lower():
            return ParseResult(
                results=[],
                has_captcha=True,
                error="SmartCaptcha detected",
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
            results = self._parse_organic_results(soup, html)
        
        if not results:
            results = self._regex_fallback(html, vertical)
        
        total_results = self.extract_total_results(html)
        
        return ParseResult(
            results=results,
            total_results=total_results,
        )
    
    def _parse_organic_results(self, soup: BeautifulSoup, html: str) -> List[SearchResult]:
        """Parse Yandex organic results"""
        results = []
        position = 0
        seen_urls = set()
        
        # Find result containers
        containers = soup.select("li.serp-item")
        if not containers:
            containers = soup.select("div[data-cid]")
        
        for container in containers:
            try:
                # Skip ads
                if container.get('data-cid', '').startswith('a'):
                    continue
                
                # Title and link
                title_elem = container.select_one("h2 a") or \
                            container.select_one("a.OrganicTitle-Link") or \
                            container.select_one("a.Link")
                
                if not title_elem:
                    continue
                
                title = self.clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                # Skip Yandex internal
                if 'yandex.' in url:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Description
                desc_elem = container.select_one("div.OrganicText") or \
                           container.select_one("span.OrganicTextContentSpan") or \
                           container.select_one("div.text-container")
                description = self.clean_text(desc_elem.get_text()) if desc_elem else ""
                
                # Displayed URL
                url_elem = container.select_one("a.Link_theme_outer") or \
                          container.select_one("div.Path a")
                displayed_url = self.clean_text(url_elem.get_text()) if url_elem else ""
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    description=description,
                    displayed_url=displayed_url,
                    source="yandex",
                ))
                
            except Exception:
                continue
        
        # Try to parse from JSON if no results
        if not results:
            results = self._parse_from_json(html)
        
        return results
    
    def _parse_from_json(self, html: str) -> List[SearchResult]:
        """Parse Yandex results from embedded JSON data"""
        results = []
        position = 0
        
        try:
            # Yandex embeds search data in script tags
            json_pattern = r'var defined_search_items\s*=\s*(\[.*?\]);'
            match = re.search(json_pattern, html, re.DOTALL)
            
            if not match:
                # Try alternate pattern
                json_pattern = r'"searchdata"\s*:\s*(\{.*?\})\s*[,}]'
                match = re.search(json_pattern, html, re.DOTALL)
            
            if match:
                data = json.loads(match.group(1))
                
                items = data if isinstance(data, list) else data.get('docs', [])
                
                seen = set()
                for item in items:
                    if isinstance(item, dict):
                        url = item.get('url', '')
                        title = item.get('title', '')
                        
                        if url and url.startswith('http') and url not in seen:
                            seen.add(url)
                            position += 1
                            
                            results.append(SearchResult(
                                position=position,
                                title=self.clean_text(title) or urlparse(url).netloc,
                                url=url,
                                description=item.get('text', ''),
                                source="yandex_json",
                            ))
                            
        except (json.JSONDecodeError, KeyError):
            pass
        
        return results
    
    def _parse_news_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse Yandex News results"""
        results = []
        position = 0
        seen_urls = set()
        
        containers = soup.select("article")
        if not containers:
            containers = soup.select("div.story")
        if not containers:
            containers = soup.select("div[data-storyid]")
        
        for container in containers:
            try:
                link_elem = container.select_one("a[href]")
                if not link_elem:
                    continue
                
                url = link_elem.get('href', '')
                if not url.startswith('http') or url in seen_urls:
                    continue
                
                if 'yandex.' in url:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Title
                title_elem = container.select_one("h2") or \
                            container.select_one("a.mg-card__link")
                title = self.clean_text(title_elem.get_text()) if title_elem else ""
                
                if not title:
                    continue
                
                # Source
                source_elem = container.select_one("span.mg-card__source-name")
                source = self.clean_text(source_elem.get_text()) if source_elem else "yandex_news"
                
                # Time
                time_elem = container.select_one("span.mg-card__age")
                date = time_elem.get_text() if time_elem else None
                
                # Thumbnail
                img_elem = container.select_one("img")
                thumbnail = img_elem.get("src") if img_elem else None
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    source=source,
                    date=date,
                    thumbnail=thumbnail,
                ))
                
            except Exception:
                continue
        
        return results
    
    def _parse_image_results(self, soup: BeautifulSoup, html: str) -> List[SearchResult]:
        """Parse Yandex Image results"""
        results = []
        position = 0
        seen_urls = set()
        
        # Yandex images use JSON data
        try:
            pattern = r'"origUrl":"([^"]+)"'
            matches = re.findall(pattern, html)
            
            for url in matches:
                if url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                results.append(SearchResult(
                    position=position,
                    title=f"Image {position}",
                    url=url,
                    source="yandex_images",
                ))
                
                if position >= 50:
                    break
                    
        except Exception:
            pass
        
        return results
    
    def _parse_video_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse Yandex Video results"""
        results = []
        position = 0
        seen_urls = set()
        
        containers = soup.select("div.serp-item")
        
        for container in containers:
            try:
                link_elem = container.select_one("a[href]")
                if not link_elem:
                    continue
                
                url = link_elem.get('href', '')
                if not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Title
                title_elem = container.select_one("div.VideoThumb-Title") or \
                            container.select_one("[title]")
                title = ""
                if title_elem:
                    title = title_elem.get('title', '') or title_elem.get_text()
                title = self.clean_text(title) or f"Video {position}"
                
                # Thumbnail
                img_elem = container.select_one("img")
                thumbnail = img_elem.get("src") if img_elem else None
                
                # Duration
                duration_elem = container.select_one("div.VideoThumb-Duration")
                extra = {}
                if duration_elem:
                    extra["duration"] = self.clean_text(duration_elem.get_text())
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    thumbnail=thumbnail,
                    source="yandex_videos",
                    extra=extra if extra else None,
                ))
                
            except Exception:
                continue
        
        return results
    
    def _regex_fallback(self, html: str, vertical: SearchVertical) -> List[SearchResult]:
        """Regex fallback for Yandex"""
        results = []
        position = 0
        seen = set()
        
        # Find URLs in the page
        urls = re.findall(r'href="(https?://(?!yandex\.)[^"]+)"', html)
        
        for url in urls:
            if url in seen:
                continue
            
            # Skip Yandex internal
            if 'yandex.' in url:
                continue
            
            # Skip common non-result patterns
            skip = ['.js', '.css', '.png', '.jpg', '.svg', 'favicon']
            if any(s in url.lower() for s in skip):
                continue
            
            seen.add(url)
            position += 1
            
            results.append(SearchResult(
                position=position,
                title=urlparse(url).netloc,
                url=url,
                source="yandex_regex",
            ))
            
            if position >= 15:
                break
        
        return results
