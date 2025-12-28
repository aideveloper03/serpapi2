"""
OmniScrape Engine - Google Search Parser
Comprehensive Google search scraper with support for all verticals
"""

import re
from typing import Optional, List
from urllib.parse import urlencode, urlparse, parse_qs
from bs4 import BeautifulSoup, Tag

from models import SearchResult, SearchVertical
from config import settings
from .base import BaseSearchEngine, ParseResult


class GoogleSearchEngine(BaseSearchEngine):
    """
    Google search engine parser with specific CSS selectors
    for organic results, news, images, and videos.
    """
    
    ENGINE_NAME = "google"
    BASE_URL = "https://www.google.com"
    SEARCH_PATH = "/search"
    NEWS_PATH = "/search"
    IMAGES_PATH = "/search"
    VIDEOS_PATH = "/search"
    DEFAULT_DELAY = settings.google_delay
    
    # CSS Selectors for organic results (updated for 2024)
    SELECTORS = {
        # Main result containers
        "result_container": [
            "div.g",
            "div[data-hveid]",
            "div.tF2Cxc",
            "div.yuRUbf",
        ],
        # Title selectors
        "title": [
            "h3",
            "h3.LC20lb",
            "h3.DKV0Md",
            "a h3",
        ],
        # Link selectors
        "link": [
            "a[href]",
            "div.yuRUbf > a",
            "a[data-ved]",
        ],
        # Description selectors
        "description": [
            "div.VwiC3b",
            "span.aCOpRe",
            "div.IsZvec",
            "div[data-sncf]",
            "div.s3v9rd",
        ],
        # Displayed URL
        "displayed_url": [
            "cite",
            "span.VuuXrf",
            "div.TbwUpd cite",
        ],
        # Date
        "date": [
            "span.MUxGbd",
            "span.LEwnzc",
            "span.f",
        ],
        # Featured snippet
        "featured_snippet": [
            "div.xpdopen",
            "div.IZE3Td",
        ],
        # Knowledge panel
        "knowledge_panel": [
            "div.kp-wholepage",
            "div.osrp-blk",
        ],
        # News results
        "news_container": [
            "div.SoaBEf",
            "g-card",
            "div.WlydOe",
        ],
        # Image results
        "image_container": [
            "div.isv-r",
            "div.ivg-i",
        ],
        # Video results
        "video_container": [
            "div.dXiKIc",
            "div.RzdJxc",
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
        """Build Google search URL"""
        
        params = {
            "q": query,
            "num": num_results,
        }
        
        # Pagination (Google uses start parameter)
        if page > 1:
            params["start"] = (page - 1) * num_results
        
        # Vertical-specific parameters
        if vertical == SearchVertical.NEWS:
            params["tbm"] = "nws"
        elif vertical == SearchVertical.IMAGES:
            params["tbm"] = "isch"
        elif vertical == SearchVertical.VIDEOS:
            params["tbm"] = "vid"
        
        # Country/region
        if country:
            params["gl"] = country.lower()
            params["cr"] = f"country{country.upper()}"
        
        # Language
        if language:
            params["hl"] = language.lower()
            params["lr"] = f"lang_{language.lower()}"
        
        # Time range
        if time_range:
            tbs_map = {
                "d": "qdr:d",   # Past day
                "w": "qdr:w",   # Past week
                "m": "qdr:m",   # Past month
                "y": "qdr:y",   # Past year
            }
            if time_range in tbs_map:
                params["tbs"] = tbs_map[time_range]
        
        # Safe search
        params["safe"] = "active" if safe_search else "off"
        
        # Additional parameters to appear more legitimate
        params["ie"] = "UTF-8"
        params["oe"] = "UTF-8"
        params["pws"] = "0"  # Disable personalized results
        params["filter"] = "0"  # Disable duplicate filtering
        
        return f"{self.BASE_URL}{self.SEARCH_PATH}?{urlencode(params)}"
    
    def parse_results(
        self,
        html: str,
        vertical: SearchVertical,
    ) -> ParseResult:
        """Parse Google search results"""
        
        # Check for CAPTCHA/blocking
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
        
        # Route to appropriate parser
        if vertical == SearchVertical.NEWS:
            results = self._parse_news_results(soup)
        elif vertical == SearchVertical.IMAGES:
            results = self._parse_image_results(soup)
        elif vertical == SearchVertical.VIDEOS:
            results = self._parse_video_results(soup)
        else:
            results = self._parse_organic_results(soup)
        
        # Try regex fallback if no results
        if not results:
            results = self._regex_fallback(html, vertical)
        
        # Extract total results count
        total_results = self.extract_total_results(html)
        
        return ParseResult(
            results=results,
            total_results=total_results,
        )
    
    def _parse_organic_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse organic search results"""
        results = []
        position = 0
        
        # Find all result containers
        containers = []
        for selector in self.SELECTORS["result_container"]:
            containers.extend(soup.select(selector))
        
        # Deduplicate by tracking seen URLs
        seen_urls = set()
        
        for container in containers:
            try:
                # Extract title
                title_elem = None
                for selector in self.SELECTORS["title"]:
                    title_elem = container.select_one(selector)
                    if title_elem:
                        break
                
                if not title_elem:
                    continue
                
                title = self.clean_text(title_elem.get_text())
                if not title:
                    continue
                
                # Extract link
                link_elem = None
                for selector in self.SELECTORS["link"]:
                    link_elem = container.select_one(selector)
                    if link_elem and link_elem.get('href'):
                        break
                
                if not link_elem:
                    continue
                
                url = self.clean_url(link_elem.get('href', ''))
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Extract description
                description = ""
                for selector in self.SELECTORS["description"]:
                    desc_elem = container.select_one(selector)
                    if desc_elem:
                        description = self.clean_text(desc_elem.get_text())
                        if description:
                            break
                
                # Extract displayed URL
                displayed_url = ""
                for selector in self.SELECTORS["displayed_url"]:
                    url_elem = container.select_one(selector)
                    if url_elem:
                        displayed_url = self.clean_text(url_elem.get_text())
                        if displayed_url:
                            break
                
                # Extract date
                date = None
                for selector in self.SELECTORS["date"]:
                    date_elem = container.select_one(selector)
                    if date_elem:
                        date = self.extract_date(date_elem.get_text())
                        if date:
                            break
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    description=description,
                    displayed_url=displayed_url,
                    date=date,
                    source="google",
                ))
                
            except Exception as e:
                continue
        
        return results
    
    def _parse_news_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse Google News results"""
        results = []
        position = 0
        seen_urls = set()
        
        # Find news containers
        containers = []
        for selector in self.SELECTORS["news_container"]:
            containers.extend(soup.select(selector))
        
        # Also check for regular result containers with news indicators
        containers.extend(soup.select("div.SoaBEf"))
        containers.extend(soup.select("article"))
        
        for container in containers:
            try:
                # Find the link
                link_elem = container.select_one("a[href]")
                if not link_elem:
                    continue
                
                url = self.clean_url(link_elem.get('href', ''))
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Title
                title_elem = container.select_one("div.mCBkyc") or \
                            container.select_one("div.n0jPhd") or \
                            container.select_one("h3") or \
                            container.select_one("h4") or \
                            link_elem
                
                title = self.clean_text(title_elem.get_text()) if title_elem else ""
                if not title:
                    continue
                
                # Description
                desc_elem = container.select_one("div.GI74Re") or \
                           container.select_one("div.VDXfz")
                description = self.clean_text(desc_elem.get_text()) if desc_elem else ""
                
                # Source
                source_elem = container.select_one("div.CEMjEf span") or \
                             container.select_one("span.WF4CUc")
                source = self.clean_text(source_elem.get_text()) if source_elem else ""
                
                # Date
                date_elem = container.select_one("div.OSrXXb span") or \
                           container.select_one("span.WG9SHc span")
                date = self.extract_date(date_elem.get_text()) if date_elem else None
                
                # Thumbnail
                img_elem = container.select_one("img")
                thumbnail = img_elem.get("src") if img_elem else None
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    description=description,
                    source=source or "google_news",
                    date=date,
                    thumbnail=thumbnail,
                ))
                
            except Exception:
                continue
        
        return results
    
    def _parse_image_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse Google Image results"""
        results = []
        position = 0
        seen_urls = set()
        
        # Find image containers
        containers = soup.select("div.isv-r")
        containers.extend(soup.select("div[data-ri]"))
        
        for container in containers:
            try:
                # Find the image link
                link_elem = container.select_one("a[href]")
                if not link_elem:
                    continue
                
                # Extract actual image URL from data attributes or href
                href = link_elem.get('href', '')
                
                # Parse the imgurl parameter
                if 'imgurl=' in href:
                    match = re.search(r'imgurl=([^&]+)', href)
                    if match:
                        from urllib.parse import unquote
                        url = unquote(match.group(1))
                    else:
                        continue
                else:
                    url = self.clean_url(href)
                
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Thumbnail
                img_elem = container.select_one("img")
                thumbnail = img_elem.get("src") if img_elem else None
                
                # Title/alt
                title = img_elem.get("alt", "") if img_elem else ""
                title = self.clean_text(title) or f"Image {position}"
                
                results.append(SearchResult(
                    position=position,
                    title=title,
                    url=url,
                    thumbnail=thumbnail,
                    source="google_images",
                ))
                
            except Exception:
                continue
        
        return results
    
    def _parse_video_results(self, soup: BeautifulSoup) -> List[SearchResult]:
        """Parse Google Video results"""
        results = []
        position = 0
        seen_urls = set()
        
        # Find video containers
        containers = soup.select("div.dXiKIc")
        containers.extend(soup.select("div.g"))
        
        for container in containers:
            try:
                # Check if it's actually a video result
                video_indicator = container.select_one("span.WGvvNb") or \
                                 container.select_one("div.RpEddb") or \
                                 container.select_one("[data-video-url]")
                
                # Find link
                link_elem = container.select_one("a[href]")
                if not link_elem:
                    continue
                
                url = self.clean_url(link_elem.get('href', ''))
                if not url or not url.startswith('http') or url in seen_urls:
                    continue
                
                # Check if it looks like a video URL
                video_domains = ['youtube.com', 'vimeo.com', 'dailymotion.com', 'twitch.tv']
                is_video = any(domain in url for domain in video_domains) or video_indicator
                
                if not is_video:
                    continue
                
                seen_urls.add(url)
                position += 1
                
                # Title
                title_elem = container.select_one("h3") or \
                            container.select_one("div.fc9yUc") or \
                            link_elem
                title = self.clean_text(title_elem.get_text()) if title_elem else f"Video {position}"
                
                # Description
                desc_elem = container.select_one("div.Uroaid")
                description = self.clean_text(desc_elem.get_text()) if desc_elem else ""
                
                # Duration
                duration_elem = container.select_one("span.WGvvNb")
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
                    description=description,
                    thumbnail=thumbnail,
                    source="google_videos",
                    extra=extra if extra else None,
                ))
                
            except Exception:
                continue
        
        return results
    
    def _regex_fallback(self, html: str, vertical: SearchVertical) -> List[SearchResult]:
        """
        Fallback parser using regex when CSS selectors fail.
        This is a last resort before using headless browser.
        """
        results = []
        position = 0
        
        # Common URL pattern in Google results
        url_pattern = r'<a[^>]+href="(/url\?q=([^"&]+)|https?://[^"]+)"[^>]*>'
        title_pattern = r'<h3[^>]*>([^<]+)</h3>'
        
        # Find all links
        urls = re.findall(r'https?://(?:www\.)?(?!google\.|gstatic\.)[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^"\'<>\s]*', html)
        
        # Deduplicate and filter
        seen = set()
        for url in urls:
            # Skip Google domains
            if 'google.' in url or 'gstatic.' in url or 'googleapis.' in url:
                continue
            
            # Skip common non-result URLs
            skip_patterns = [
                r'/policies/',
                r'/preferences',
                r'/advanced_search',
                r'accounts\.google',
                r'maps\.google',
                r'play\.google',
            ]
            if any(re.search(p, url) for p in skip_patterns):
                continue
            
            if url not in seen:
                seen.add(url)
                position += 1
                
                # Try to extract title near the URL
                url_pos = html.find(url)
                context_start = max(0, url_pos - 500)
                context_end = min(len(html), url_pos + 500)
                context = html[context_start:context_end]
                
                title_match = re.search(r'<h3[^>]*>([^<]+)</h3>', context)
                title = title_match.group(1) if title_match else urlparse(url).netloc
                
                results.append(SearchResult(
                    position=position,
                    title=self.clean_text(title),
                    url=url,
                    source="google_regex",
                ))
                
                if position >= 20:  # Limit fallback results
                    break
        
        return results
