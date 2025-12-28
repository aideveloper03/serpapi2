"""
OmniScrape Engine - DuckDuckGo Search Parser
DuckDuckGo search scraper - privacy-focused engine with less aggressive blocking
"""

import re
import json
from typing import Optional, List
from urllib.parse import urlencode, urlparse, quote_plus
from bs4 import BeautifulSoup

from models import SearchResult, SearchVertical
from config import settings
from .base import BaseSearchEngine, ParseResult


class DuckDuckGoSearchEngine(BaseSearchEngine):
    """
    DuckDuckGo search engine parser.
    DDG is more forgiving with scraping but uses JavaScript heavily.
    """
    
    ENGINE_NAME = "duckduckgo"
    BASE_URL = "https://duckduckgo.com"
    HTML_URL = "https://html.duckduckgo.com/html"
    SEARCH_PATH = "/"
    NEWS_PATH = "/"
    IMAGES_PATH = "/"
    VIDEOS_PATH = "/"
    DEFAULT_DELAY = settings.duckduckgo_delay
    
    # CSS Selectors for DuckDuckGo HTML version
    SELECTORS = {
        "result_container": [
            "div.result",
            "div.results_links",
            "div.result__body",
        ],
        "title": [
            "a.result__a",
            "h2.result__title a",
            "a.result__snippet",
        ],
        "link": [
            "a.result__a[href]",
            "a.result__url[href]",
        ],
        "description": [
            "a.result__snippet",
            "div.result__snippet",
        ],
        "displayed_url": [
            "a.result__url",
            "span.result__url__domain",
        ],
        "news_container": [
            "div.result--news",
            "article.result",
        ],
        "image_container": [
            "div.tile",
            "div.tile--img",
        ],
        "video_container": [
            "div.tile--vid",
            "div.result--video",
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
        """Build DuckDuckGo search URL (HTML version for easier scraping)"""
        
        params = {
            "q": query,
        }
        
        # Vertical
        if vertical == SearchVertical.NEWS:
            params["iar"] = "news"
            params["ia"] = "news"
        elif vertical == SearchVertical.IMAGES:
            params["iar"] = "images"
            params["ia"] = "images"
        elif vertical == SearchVertical.VIDEOS:
            params["iar"] = "videos"
            params["ia"] = "videos"
        
        # Pagination (DDG HTML uses 's' parameter)
        if page > 1:
            params["s"] = str((page - 1) * 30)
            params["dc"] = str((page - 1) * 30 + 1)
        
        # Region/country
        if country:
            region_map = {
                "us": "us-en",
                "uk": "uk-en",
                "de": "de-de",
                "fr": "fr-fr",
                "es": "es-es",
                "it": "it-it",
                "jp": "jp-jp",
                "br": "br-pt",
                "au": "au-en",
                "ca": "ca-en",
            }
            params["kl"] = region_map.get(country.lower(), f"{country.lower()}-en")
        
        # Time range
        if time_range:
            time_map = {
                "d": "d",
                "w": "w",
                "m": "m",
                "y": "y",
            }
            if time_range in time_map:
                params["df"] = time_map[time_range]
        
        # Safe search
        params["kp"] = "1" if safe_search else "-2"
        
        # Use HTML version for easier parsing (no JavaScript)
        return f"{self.HTML_URL}/?{urlencode(params)}"
    
    def parse_results(
        self,
        html: str,
        vertical: SearchVertical,
    ) -> ParseResult:
        """Parse DuckDuckGo search results"""
        
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
        
        return ParseResult(
            results=results,
            total_results=None,  # DDG doesn't show total count
        )
    
    def _parse_organic_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse DuckDuckGo organic results"""
        results = []
        position = 0
        seen_urls = set()
        
        # Find result containers
        containers = soup.select("div.result")
        if not containers:
            containers = soup.select("div.results_links")
        
        for container in containers:
            try:
                # Skip ads
                if container.get('class') and 'result--ad' in container.get('class', []):
                    continue
                
                # Title and link
                title_elem = container.select_one("a.result__a")
                if not title_elem:
                    continue
                
                title = self.clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                
                # DDG sometimes uses redirect URLs
                if 'duckduckgo.com/l/' in url:
                    # Extract actual URL from uddg parameter
                    match = re.search(r'uddg=([^&]+)', url)
                    if match:
                        from urllib.parse import unquote
                        url = unquote(match.group(1))
                
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Description
                desc_elem = container.select_one("a.result__snippet")
                description = self.clean_text(desc_elem.get_text()) if desc_elem else ""
                
                # Displayed URL
                url_elem = container.select_one("a.result__url")
                displayed_url = self.clean_text(url_elem.get_text()) if url_elem else ""
                
                # Icon/favicon
                icon_elem = container.select_one("img.result__icon__img")
                favicon = icon_elem.get('src') if icon_elem else None
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    description=description,
                    displayed_url=displayed_url,
                    source="duckduckgo",
                ))
                
            except Exception:
                continue
        
        return results
    
    def _parse_news_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse DuckDuckGo News results"""
        results = []
        position = 0
        seen_urls = set()
        
        # DDG news uses similar structure to organic
        containers = soup.select("div.result--news")
        if not containers:
            containers = soup.select("div.result")
        
        for container in containers:
            try:
                title_elem = container.select_one("a.result__a")
                if not title_elem:
                    continue
                
                title = self.clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                
                if 'duckduckgo.com/l/' in url:
                    match = re.search(r'uddg=([^&]+)', url)
                    if match:
                        from urllib.parse import unquote
                        url = unquote(match.group(1))
                
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Description
                desc_elem = container.select_one("a.result__snippet")
                description = self.clean_text(desc_elem.get_text()) if desc_elem else ""
                
                # Source and date
                source_elem = container.select_one("span.result__url__domain")
                source = self.clean_text(source_elem.get_text()) if source_elem else "duckduckgo_news"
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    description=description,
                    source=source,
                ))
                
            except Exception:
                continue
        
        return results
    
    def _parse_image_results(self, soup: BeautifulSoup, html: str) -> List[SearchResult]:
        """Parse DuckDuckGo Image results"""
        results = []
        position = 0
        seen_urls = set()
        
        # DDG images use JavaScript, try to extract from vqd data
        # Look for image data in the page
        try:
            # Find JSON data in script tags
            scripts = soup.find_all('script')
            for script in scripts:
                text = script.string or ''
                if 'DDG.duckbar.load' in text or 'images' in text.lower():
                    # Try to extract image URLs
                    img_urls = re.findall(r'"image":"([^"]+)"', text)
                    thumbnails = re.findall(r'"thumbnail":"([^"]+)"', text)
                    titles = re.findall(r'"title":"([^"]+)"', text)
                    
                    for i, img_url in enumerate(img_urls):
                        if img_url in seen_urls:
                            continue
                        
                        seen_urls.add(img_url)
                        position += 1
                        
                        results.append(SearchResult(
                            position=position,
                            title=titles[i] if i < len(titles) else f"Image {position}",
                            url=img_url,
                            thumbnail=thumbnails[i] if i < len(thumbnails) else None,
                            source="duckduckgo_images",
                        ))
                        
                        if position >= 50:
                            break
        except Exception:
            pass
        
        return results
    
    def _parse_video_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse DuckDuckGo Video results"""
        results = []
        position = 0
        seen_urls = set()
        
        containers = soup.select("div.tile--vid")
        if not containers:
            containers = soup.select("div.result--video")
        
        for container in containers:
            try:
                link_elem = container.select_one("a[href]")
                if not link_elem:
                    continue
                
                url = link_elem.get('href', '')
                if 'duckduckgo.com/l/' in url:
                    match = re.search(r'uddg=([^&]+)', url)
                    if match:
                        from urllib.parse import unquote
                        url = unquote(match.group(1))
                
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Title
                title_elem = container.select_one("h6") or container.select_one("[title]")
                title = ""
                if title_elem:
                    title = title_elem.get('title', '') or title_elem.get_text()
                title = self.clean_text(title) or f"Video {position}"
                
                # Thumbnail
                img_elem = container.select_one("img")
                thumbnail = img_elem.get('src') if img_elem else None
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    thumbnail=thumbnail,
                    source="duckduckgo_videos",
                ))
                
            except Exception:
                continue
        
        return results
    
    def _regex_fallback(self, html: str, vertical: SearchVertical) -> List[SearchResult]:
        """Regex fallback for DuckDuckGo"""
        results = []
        position = 0
        seen = set()
        
        # Extract uddg parameter URLs
        uddg_matches = re.findall(r'uddg=([^&"]+)', html)
        
        for match in uddg_matches:
            try:
                from urllib.parse import unquote
                url = unquote(match)
                
                if not url.startswith('http') or url in seen:
                    continue
                
                if 'duckduckgo.com' in url:
                    continue
                
                seen.add(url)
                position += 1
                
                results.append(SearchResult(
                    position=position,
                    title=urlparse(url).netloc,
                    url=url,
                    source="duckduckgo_regex",
                ))
                
                if position >= 20:
                    break
                    
            except Exception:
                continue
        
        return results
