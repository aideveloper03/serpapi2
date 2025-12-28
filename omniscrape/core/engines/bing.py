"""
OmniScrape Engine - Bing Search Parser
Comprehensive Bing search scraper with support for all verticals
"""

import re
from typing import Optional, List
from urllib.parse import urlencode, urlparse, unquote
from bs4 import BeautifulSoup

from models import SearchResult, SearchVertical
from config import settings
from .base import BaseSearchEngine, ParseResult


class BingSearchEngine(BaseSearchEngine):
    """
    Bing search engine parser with specific CSS selectors
    for organic results, news, images, and videos.
    """
    
    ENGINE_NAME = "bing"
    BASE_URL = "https://www.bing.com"
    SEARCH_PATH = "/search"
    NEWS_PATH = "/news/search"
    IMAGES_PATH = "/images/search"
    VIDEOS_PATH = "/videos/search"
    DEFAULT_DELAY = settings.bing_delay
    
    # CSS Selectors for Bing (updated for 2024)
    SELECTORS = {
        # Main result containers
        "result_container": [
            "li.b_algo",
            "div.b_algo",
            "li.b_ans",
        ],
        # Title
        "title": [
            "h2 a",
            "h2",
            "a.tilk",
        ],
        # Link
        "link": [
            "h2 a[href]",
            "a.tilk[href]",
        ],
        # Description
        "description": [
            "div.b_caption p",
            "p.b_algoSlug",
            "div.b_snippet",
            "p",
        ],
        # Displayed URL
        "displayed_url": [
            "cite",
            "div.b_attribution cite",
        ],
        # Date
        "date": [
            "span.news_dt",
            "span.b_dateline",
        ],
        # News
        "news_container": [
            "div.news-card",
            "div.newsitem",
            "article",
        ],
        # Images
        "image_container": [
            "div.imgpt",
            "li.iusc",
            "div.iusc",
        ],
        # Videos
        "video_container": [
            "div.mc_vtvc",
            "div.dg_u",
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
        """Build Bing search URL"""
        
        params = {
            "q": query,
            "count": num_results,
        }
        
        # Pagination (Bing uses first parameter)
        if page > 1:
            params["first"] = ((page - 1) * num_results) + 1
        
        # Determine path based on vertical
        if vertical == SearchVertical.NEWS:
            path = self.NEWS_PATH
        elif vertical == SearchVertical.IMAGES:
            path = self.IMAGES_PATH
        elif vertical == SearchVertical.VIDEOS:
            path = self.VIDEOS_PATH
        else:
            path = self.SEARCH_PATH
        
        # Market (combines country and language)
        if country and language:
            params["mkt"] = f"{language}-{country}"
        elif language:
            params["setlang"] = language
        
        # Time range
        if time_range:
            time_map = {
                "d": "ex1:\"ez1\"",  # Past day
                "w": "ex1:\"ez2\"",  # Past week
                "m": "ex1:\"ez3\"",  # Past month
            }
            if time_range in time_map:
                params["filters"] = time_map[time_range]
        
        # Safe search
        params["safeSearch"] = "Strict" if safe_search else "Off"
        
        return f"{self.BASE_URL}{path}?{urlencode(params)}"
    
    def parse_results(
        self,
        html: str,
        vertical: SearchVertical,
    ) -> ParseResult:
        """Parse Bing search results"""
        
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
    
    def _parse_organic_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse Bing organic search results"""
        results = []
        position = 0
        seen_urls = set()
        
        containers = []
        for selector in self.SELECTORS["result_container"]:
            containers.extend(soup.select(selector))
        
        for container in containers:
            try:
                # Title and link
                title_elem = None
                link_elem = None
                
                for selector in self.SELECTORS["title"]:
                    title_elem = container.select_one(selector)
                    if title_elem:
                        break
                
                if not title_elem:
                    continue
                
                # Get link
                if title_elem.name == 'a':
                    link_elem = title_elem
                else:
                    link_elem = title_elem.find_parent('a') or container.select_one('a[href]')
                
                if not link_elem:
                    continue
                
                url = link_elem.get('href', '')
                url = self._decode_bing_url(url)
                
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                # Skip Bing internal URLs
                if 'bing.com' in url and '/ck/' not in url:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                title = self.clean_text(title_elem.get_text())
                if not title:
                    continue
                
                # Description
                description = ""
                for selector in self.SELECTORS["description"]:
                    desc_elem = container.select_one(selector)
                    if desc_elem:
                        description = self.clean_text(desc_elem.get_text())
                        if description:
                            break
                
                # Displayed URL
                displayed_url = ""
                for selector in self.SELECTORS["displayed_url"]:
                    url_elem = container.select_one(selector)
                    if url_elem:
                        displayed_url = self.clean_text(url_elem.get_text())
                        if displayed_url:
                            break
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    description=description,
                    displayed_url=displayed_url,
                    source="bing",
                ))
                
            except Exception:
                continue
        
        return results
    
    def _parse_news_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse Bing News results"""
        results = []
        position = 0
        seen_urls = set()
        
        # Find news cards
        containers = soup.select("div.news-card")
        containers.extend(soup.select("div.newsitem"))
        containers.extend(soup.select("a.news-card"))
        
        for container in containers:
            try:
                # Get link
                if container.name == 'a':
                    link_elem = container
                else:
                    link_elem = container.select_one("a[href]")
                
                if not link_elem:
                    continue
                
                url = self._decode_bing_url(link_elem.get('href', ''))
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Title
                title_elem = container.select_one("div.title") or \
                            container.select_one("a.title") or \
                            container.select_one("[title]")
                
                title = ""
                if title_elem:
                    title = title_elem.get('title', '') or title_elem.get_text()
                title = self.clean_text(title)
                
                if not title:
                    continue
                
                # Description
                desc_elem = container.select_one("div.snippet") or \
                           container.select_one("div.desc")
                description = self.clean_text(desc_elem.get_text()) if desc_elem else ""
                
                # Source
                source_elem = container.select_one("div.source") or \
                             container.select_one("span.source")
                source = self.clean_text(source_elem.get_text()) if source_elem else "bing_news"
                
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
        """Parse Bing Image results"""
        results = []
        position = 0
        seen_urls = set()
        
        # Bing images store data in JSON within the page
        # Try to extract from iusc elements
        containers = soup.select("a.iusc")
        
        for container in containers:
            try:
                import json
                
                # Get metadata from 'm' attribute
                metadata = container.get('m', '')
                if metadata:
                    try:
                        data = json.loads(metadata)
                        url = data.get('murl', '')
                        title = data.get('t', '')
                        thumbnail = data.get('turl', '')
                    except json.JSONDecodeError:
                        continue
                else:
                    continue
                
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                results.append(SearchResult(
                    position=position,
                    title=self.clean_text(title) or f"Image {position}",
                    url=url,
                    thumbnail=thumbnail,
                    source="bing_images",
                ))
                
            except Exception:
                continue
        
        return results
    
    def _parse_video_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse Bing Video results"""
        results = []
        position = 0
        seen_urls = set()
        
        containers = soup.select("div.mc_vtvc")
        containers.extend(soup.select("div.dg_u"))
        
        for container in containers:
            try:
                link_elem = container.select_one("a[href]")
                if not link_elem:
                    continue
                
                url = self._decode_bing_url(link_elem.get('href', ''))
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Title
                title_elem = container.select_one("div.mc_vtvc_title") or \
                            container.select_one("[title]")
                title = ""
                if title_elem:
                    title = title_elem.get('title', '') or title_elem.get_text()
                title = self.clean_text(title) or f"Video {position}"
                
                # Duration
                duration_elem = container.select_one("span.mc_bc_rc_w")
                extra = {}
                if duration_elem:
                    extra["duration"] = self.clean_text(duration_elem.get_text())
                
                # Thumbnail
                img_elem = container.select_one("img")
                thumbnail = img_elem.get("src") if img_elem else None
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    thumbnail=thumbnail,
                    source="bing_videos",
                    extra=extra if extra else None,
                ))
                
            except Exception:
                continue
        
        return results
    
    def _decode_bing_url(self, url: str) -> str:
        """Decode Bing tracking URLs to get the actual URL"""
        if not url:
            return ""
        
        # Handle Bing redirect URLs
        if '/ck/' in url or 'bing.com/ck' in url:
            # Try to extract from u parameter
            match = re.search(r'[?&]u=a1([^&]+)', url)
            if match:
                try:
                    import base64
                    # Bing uses a modified base64 encoding
                    encoded = match.group(1)
                    # Add padding if needed
                    padding = 4 - len(encoded) % 4
                    if padding != 4:
                        encoded += '=' * padding
                    decoded = base64.urlsafe_b64decode(encoded).decode('utf-8')
                    return decoded
                except:
                    pass
        
        return self.clean_url(url)
    
    def _regex_fallback(self, html: str, vertical: SearchVertical) -> List[SearchResult]:
        """Regex fallback parser for Bing"""
        results = []
        position = 0
        seen = set()
        
        # Find URLs that are likely results
        urls = re.findall(r'href="(https?://(?!www\.bing\.)[^"]+)"', html)
        
        for url in urls:
            # Skip tracking URLs
            if '/ck/' in url or 'bing.com' in url:
                url = self._decode_bing_url(url)
            
            if not url or not url.startswith('http') or url in seen:
                continue
            
            # Skip common non-result URLs
            skip_patterns = [
                r'microsoft\.com',
                r'bing\.com',
                r'msn\.com/spartan',
                r'/favicon',
                r'\.js$',
                r'\.css$',
            ]
            if any(re.search(p, url) for p in skip_patterns):
                continue
            
            seen.add(url)
            position += 1
            
            results.append(SearchResult(
                position=position,
                title=urlparse(url).netloc,
                url=url,
                source="bing_regex",
            ))
            
            if position >= 15:
                break
        
        return results
