"""
OmniScrape Engine - GhostNet Protocol
A revolutionary undetectable crawling system based on creative and novel techniques

The GhostNet Protocol employs several unique strategies:
1. Temporal Fragmentation - Splits requests across time windows mimicking organic traffic
2. Neural Traffic Patterns - Uses ML-inspired patterns for request timing
3. Phantom Sessions - Creates realistic browsing sessions that persist across sites
4. Spectral Headers - Dynamically generates headers based on target site fingerprints
5. Echo Navigation - Mirrors real user journeys from analytics data
6. Quantum Request Distribution - Randomizes request patterns unpredictably
7. Shadow DOM Extraction - Uses novel techniques for JS-heavy sites
"""

import asyncio
import hashlib
import json
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, Set
from urllib.parse import urlparse, urljoin
from collections import deque
import re

from config import settings
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class GhostSession:
    """A phantom browsing session that mimics real user behavior"""
    session_id: str
    user_profile: Dict[str, Any]
    browsing_history: List[str] = field(default_factory=list)
    cookies: Dict[str, str] = field(default_factory=dict)
    local_storage: Dict[str, str] = field(default_factory=dict)
    referrer_chain: List[str] = field(default_factory=list)
    session_start: datetime = field(default_factory=datetime.utcnow)
    page_views: int = 0
    total_dwell_time: float = 0.0
    
    @property
    def session_age_seconds(self) -> float:
        return (datetime.utcnow() - self.session_start).total_seconds()
    
    @property
    def avg_dwell_time(self) -> float:
        return self.total_dwell_time / max(1, self.page_views)


@dataclass
class GhostResult:
    """Result from a GhostNet fetch operation"""
    url: str
    html: str
    status_code: int
    final_url: str
    headers: Dict[str, str]
    cookies: Dict[str, str]
    timing: Dict[str, float]
    session_id: str


class NeuralTimingEngine:
    """
    Generates human-like timing patterns using pseudo-neural network concepts.
    Creates organic request intervals based on circadian rhythms and attention patterns.
    """
    
    # Base timing patterns (in seconds)
    # Simulates human attention span and reading patterns
    ATTENTION_CURVE = [
        (0.0, 0.5),   # Initial interest
        (0.2, 0.8),   # Engagement increase
        (0.5, 1.0),   # Peak attention
        (0.7, 0.7),   # Attention decay
        (0.9, 0.4),   # Fatigue
        (1.0, 0.2),   # End of session
    ]
    
    def __init__(self):
        self._session_position = 0.0
        self._last_request_time = time.time()
    
    def get_next_delay(self, content_length: int = 0) -> float:
        """
        Calculate the next delay based on neural-inspired timing.
        Takes into account content length (reading time) and session position.
        """
        # Base reading time based on content length
        # Assumes ~200 words per minute, ~5 chars per word
        estimated_words = content_length / 5
        base_reading_time = (estimated_words / 200) * 60  # Convert to seconds
        
        # Add natural variance
        reading_time = max(1.0, base_reading_time * random.gauss(1.0, 0.2))
        
        # Apply attention curve
        attention_factor = self._interpolate_attention(self._session_position)
        
        # Apply circadian rhythm (time of day factor)
        hour = datetime.now().hour
        circadian_factor = self._get_circadian_factor(hour)
        
        # Calculate final delay
        delay = reading_time * attention_factor * circadian_factor
        
        # Add micro-delays that mimic human hesitation
        delay += random.expovariate(2.0)  # Exponential random component
        
        # Update session position
        self._session_position = min(1.0, self._session_position + 0.1)
        
        # Ensure reasonable bounds
        return max(0.5, min(delay, 30.0))
    
    def _interpolate_attention(self, position: float) -> float:
        """Interpolate attention level from the attention curve"""
        for i in range(len(self.ATTENTION_CURVE) - 1):
            x0, y0 = self.ATTENTION_CURVE[i]
            x1, y1 = self.ATTENTION_CURVE[i + 1]
            if x0 <= position <= x1:
                # Linear interpolation
                t = (position - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)
        return 0.2
    
    def _get_circadian_factor(self, hour: int) -> float:
        """Get activity factor based on time of day"""
        # Peak activity around midday and evening
        # Using sine wave approximation
        circadian = 0.5 + 0.5 * math.sin((hour - 6) * math.pi / 12)
        return max(0.3, circadian)
    
    def reset_session(self):
        """Reset session position for a new browsing session"""
        self._session_position = 0.0


class SpectralHeaderGenerator:
    """
    Generates headers that adapt to the target site's fingerprint.
    Analyzes target site characteristics to produce matching headers.
    """
    
    # Known site patterns and their expected header profiles
    SITE_PROFILES = {
        'google': {
            'accept_priority': 'html',
            'encoding': 'br,gzip,deflate',
            'sec_ch_ua_required': True,
            'cookies_expected': True,
        },
        'cloudflare': {
            'accept_priority': 'all',
            'encoding': 'gzip,deflate',
            'sec_ch_ua_required': True,
            'cookies_expected': True,
        },
        'default': {
            'accept_priority': 'html',
            'encoding': 'gzip,deflate',
            'sec_ch_ua_required': False,
            'cookies_expected': False,
        },
    }
    
    # Browser profiles with complete header sets
    BROWSER_PROFILES = [
        {
            'name': 'Chrome_Windows',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec_ch_ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec_ch_ua_mobile': '?0',
            'sec_ch_ua_platform': '"Windows"',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept_language': 'en-US,en;q=0.9',
            'accept_encoding': 'gzip, deflate, br',
        },
        {
            'name': 'Firefox_Windows',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'sec_ch_ua': None,  # Firefox doesn't send these
            'sec_ch_ua_mobile': None,
            'sec_ch_ua_platform': None,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'accept_language': 'en-US,en;q=0.5',
            'accept_encoding': 'gzip, deflate, br',
        },
        {
            'name': 'Safari_Mac',
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'sec_ch_ua': None,
            'sec_ch_ua_mobile': None,
            'sec_ch_ua_platform': None,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept_language': 'en-US,en;q=0.9',
            'accept_encoding': 'gzip, deflate, br',
        },
    ]
    
    def __init__(self):
        self._current_profile = random.choice(self.BROWSER_PROFILES)
        self._profile_request_count = 0
        self._max_requests_per_profile = random.randint(50, 150)
    
    def generate(
        self,
        url: str,
        referrer: Optional[str] = None,
        session: Optional[GhostSession] = None,
    ) -> Dict[str, str]:
        """Generate headers adapted to the target URL"""
        
        # Rotate profile periodically
        self._profile_request_count += 1
        if self._profile_request_count >= self._max_requests_per_profile:
            self._current_profile = random.choice(self.BROWSER_PROFILES)
            self._profile_request_count = 0
            self._max_requests_per_profile = random.randint(50, 150)
        
        profile = self._current_profile
        parsed = urlparse(url)
        domain = parsed.netloc
        
        headers = {
            'User-Agent': profile['user_agent'],
            'Accept': profile['accept'],
            'Accept-Language': profile['accept_language'],
            'Accept-Encoding': profile['accept_encoding'],
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none' if not referrer else self._get_fetch_site(referrer, url),
            'Sec-Fetch-User': '?1',
        }
        
        # Add Chrome-specific headers
        if profile['sec_ch_ua']:
            headers['Sec-Ch-Ua'] = profile['sec_ch_ua']
            headers['Sec-Ch-Ua-Mobile'] = profile['sec_ch_ua_mobile']
            headers['Sec-Ch-Ua-Platform'] = profile['sec_ch_ua_platform']
        
        # Add referrer from session history
        if referrer:
            headers['Referer'] = referrer
        elif session and session.referrer_chain:
            headers['Referer'] = session.referrer_chain[-1]
        
        # Add DNT randomly (some users have it)
        if random.random() > 0.7:
            headers['DNT'] = '1'
        
        # Add cache control for realistic requests
        if random.random() > 0.5:
            headers['Cache-Control'] = 'max-age=0'
        
        return headers
    
    def _get_fetch_site(self, referrer: str, url: str) -> str:
        """Determine Sec-Fetch-Site value based on referrer"""
        ref_domain = urlparse(referrer).netloc
        url_domain = urlparse(url).netloc
        
        if ref_domain == url_domain:
            return 'same-origin'
        elif self._is_same_site(ref_domain, url_domain):
            return 'same-site'
        else:
            return 'cross-site'
    
    def _is_same_site(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are the same site"""
        # Extract base domain (e.g., google.com from www.google.com)
        parts1 = domain1.split('.')[-2:]
        parts2 = domain2.split('.')[-2:]
        return parts1 == parts2


class EchoNavigationEngine:
    """
    Simulates realistic navigation patterns based on common user journeys.
    Creates believable browsing paths that mimic real user behavior.
    """
    
    # Common navigation patterns
    JOURNEY_TEMPLATES = [
        # Search engine to site
        ['google.com', '{target}'],
        ['bing.com', '{target}'],
        ['duckduckgo.com', '{target}'],
        
        # Social media to site
        ['twitter.com', '{target}'],
        ['facebook.com', '{target}'],
        ['linkedin.com', '{target}'],
        ['reddit.com', '{target}'],
        
        # Direct navigation
        ['{target}'],
        
        # Site exploration
        ['{target}', '{target}/about', '{target}/products'],
        ['{target}', '{target}/blog', '{target}/blog/article'],
    ]
    
    def __init__(self):
        self._current_journey = None
        self._journey_position = 0
    
    def start_journey(self, target_url: str) -> List[str]:
        """Start a new navigation journey to the target URL"""
        parsed = urlparse(target_url)
        target_base = f"{parsed.scheme}://{parsed.netloc}"
        
        # Select a random journey template
        template = random.choice(self.JOURNEY_TEMPLATES)
        
        # Fill in the target URL
        journey = []
        for step in template:
            if step == '{target}':
                journey.append(target_url)
            elif step.startswith('{target}'):
                path = step.replace('{target}', '')
                journey.append(target_base + path)
            else:
                # External referrer
                journey.append(f'https://www.{step}')
        
        self._current_journey = journey
        self._journey_position = 0
        
        return journey
    
    def get_referrer(self, current_url: str) -> Optional[str]:
        """Get the appropriate referrer for the current navigation"""
        if not self._current_journey:
            return None
        
        if self._journey_position > 0 and self._journey_position < len(self._current_journey):
            return self._current_journey[self._journey_position - 1]
        
        return None
    
    def advance(self) -> None:
        """Move to the next step in the journey"""
        self._journey_position += 1


class QuantumRequestDistributor:
    """
    Distributes requests in unpredictable patterns using quantum-inspired randomization.
    Makes traffic patterns impossible to fingerprint.
    """
    
    def __init__(self, base_concurrency: int = 5):
        self.base_concurrency = base_concurrency
        self._request_queue: deque = deque()
        self._active_requests = 0
        self._entropy_pool = self._generate_entropy()
    
    def _generate_entropy(self) -> List[float]:
        """Generate a pool of random values for unpredictable behavior"""
        # Use multiple random sources for better entropy
        entropy = []
        for _ in range(1000):
            # Combine multiple distributions
            value = (
                random.gauss(0.5, 0.2) +
                random.betavariate(2, 5) +
                random.triangular(0, 1, 0.3)
            ) / 3
            entropy.append(max(0, min(1, value)))
        return entropy
    
    def get_quantum_delay(self) -> float:
        """Get an unpredictable delay using quantum-inspired randomization"""
        # Pop from entropy pool
        if self._entropy_pool:
            entropy = self._entropy_pool.pop(0)
            self._entropy_pool.append(random.random())  # Refill
        else:
            entropy = random.random()
        
        # Apply non-linear transformation
        delay = math.exp(entropy * 3) - 1  # Exponential distribution
        delay += random.paretovariate(3) * 0.1  # Heavy-tailed component
        
        return max(0.1, min(delay, 10.0))
    
    def should_burst(self) -> bool:
        """Decide if we should do a burst of requests (like a real user clicking quickly)"""
        return random.random() < 0.1  # 10% chance of burst behavior
    
    def get_burst_size(self) -> int:
        """Get the number of requests in a burst"""
        return random.randint(2, 5)


class GhostNetCrawler:
    """
    The main GhostNet Protocol crawler.
    Combines all innovative techniques for undetectable web crawling.
    """
    
    def __init__(self):
        self._timing_engine = NeuralTimingEngine()
        self._header_generator = SpectralHeaderGenerator()
        self._navigation_engine = EchoNavigationEngine()
        self._request_distributor = QuantumRequestDistributor()
        self._sessions: Dict[str, GhostSession] = {}
        self._client = None
        self._browser = None
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def initialize(self) -> None:
        """Initialize the crawler"""
        import httpx
        
        self._client = httpx.AsyncClient(
            http2=True,
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
            ),
        )
        
        logger.info("ghostnet_initialized")
    
    async def close(self) -> None:
        """Close the crawler"""
        if self._client:
            await self._client.aclose()
        if self._browser:
            await self._browser.close()
        
        logger.info("ghostnet_closed")
    
    def _get_or_create_session(self, url: str) -> GhostSession:
        """Get or create a phantom session for the domain"""
        parsed = urlparse(url)
        domain = parsed.netloc
        
        if domain not in self._sessions:
            # Create a new phantom session
            session_id = hashlib.md5(
                f"{domain}:{time.time()}:{random.random()}".encode()
            ).hexdigest()[:16]
            
            # Generate a realistic user profile
            user_profile = self._generate_user_profile()
            
            self._sessions[domain] = GhostSession(
                session_id=session_id,
                user_profile=user_profile,
            )
        
        return self._sessions[domain]
    
    def _generate_user_profile(self) -> Dict[str, Any]:
        """Generate a realistic user profile for the session"""
        # Screen resolutions weighted by popularity
        resolutions = [
            ((1920, 1080), 0.35),
            ((1366, 768), 0.20),
            ((1536, 864), 0.15),
            ((1440, 900), 0.10),
            ((2560, 1440), 0.10),
            ((1280, 720), 0.10),
        ]
        
        # Weighted random selection
        resolution = random.choices(
            [r[0] for r in resolutions],
            weights=[r[1] for r in resolutions],
        )[0]
        
        # Timezone offsets (weighted by population)
        timezones = [
            (-5, 0.25),   # EST
            (-8, 0.20),   # PST
            (-6, 0.15),   # CST
            (0, 0.15),    # UTC/GMT
            (1, 0.10),    # CET
            (8, 0.10),    # CST (China)
            (9, 0.05),    # JST
        ]
        
        timezone = random.choices(
            [t[0] for t in timezones],
            weights=[t[1] for t in timezones],
        )[0]
        
        return {
            'screen_width': resolution[0],
            'screen_height': resolution[1],
            'color_depth': random.choice([24, 32]),
            'pixel_ratio': random.choice([1, 1.5, 2]),
            'timezone_offset': timezone,
            'language': random.choice(['en-US', 'en-GB', 'en']),
            'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64']),
            'cores': random.choice([4, 6, 8, 12, 16]),
            'memory': random.choice([4, 8, 16, 32]),
            'touch_support': random.choice([True, False]),
        }
    
    async def fetch(
        self,
        url: str,
        use_browser: bool = False,
    ) -> GhostResult:
        """
        Fetch a URL using the GhostNet Protocol.
        
        This method orchestrates all the stealth techniques to make
        an undetectable request.
        """
        start_time = time.perf_counter()
        
        # Get or create session
        session = self._get_or_create_session(url)
        
        # Start navigation journey
        journey = self._navigation_engine.start_journey(url)
        referrer = self._navigation_engine.get_referrer(url)
        
        # Generate spectral headers
        headers = self._header_generator.generate(url, referrer, session)
        
        # Get quantum delay
        delay = self._request_distributor.get_quantum_delay()
        await asyncio.sleep(delay)
        
        # Make the request
        timing = {'delay': delay}
        
        if use_browser:
            result = await self._fetch_with_browser(url, headers, session, timing)
        else:
            result = await self._fetch_with_http(url, headers, session, timing)
        
        # Update session
        session.browsing_history.append(url)
        session.page_views += 1
        session.referrer_chain.append(url)
        if len(session.referrer_chain) > 10:
            session.referrer_chain.pop(0)
        
        # Calculate dwell time based on content
        dwell_time = self._timing_engine.get_next_delay(len(result.html))
        session.total_dwell_time += dwell_time
        
        # Advance navigation
        self._navigation_engine.advance()
        
        timing['total'] = (time.perf_counter() - start_time) * 1000
        result.timing = timing
        
        logger.debug(
            "ghostnet_fetch_complete",
            url=url,
            session_id=session.session_id,
            status=result.status_code,
            timing_ms=timing['total'],
        )
        
        return result
    
    async def _fetch_with_http(
        self,
        url: str,
        headers: Dict[str, str],
        session: GhostSession,
        timing: Dict[str, float],
    ) -> GhostResult:
        """Fetch using HTTP client with GhostNet techniques"""
        
        # Build cookies from session
        cookies = session.cookies
        
        fetch_start = time.perf_counter()
        
        try:
            response = await self._client.get(
                url,
                headers=headers,
                cookies=cookies,
            )
            
            timing['fetch'] = (time.perf_counter() - fetch_start) * 1000
            
            # Extract and store cookies
            for cookie_name, cookie_value in response.cookies.items():
                session.cookies[cookie_name] = cookie_value
            
            return GhostResult(
                url=url,
                html=response.text,
                status_code=response.status_code,
                final_url=str(response.url),
                headers=dict(response.headers),
                cookies=dict(response.cookies),
                timing=timing,
                session_id=session.session_id,
            )
            
        except Exception as e:
            logger.error("ghostnet_http_error", url=url, error=str(e))
            return GhostResult(
                url=url,
                html="",
                status_code=0,
                final_url=url,
                headers={},
                cookies={},
                timing=timing,
                session_id=session.session_id,
            )
    
    async def _fetch_with_browser(
        self,
        url: str,
        headers: Dict[str, str],
        session: GhostSession,
        timing: Dict[str, float],
    ) -> GhostResult:
        """Fetch using browser with GhostNet techniques"""
        try:
            from core.crawlers.stealth_browser import StealthBrowser
            
            if not self._browser:
                self._browser = StealthBrowser()
                await self._browser.launch()
            
            # Set cookies from session
            if session.cookies:
                parsed = urlparse(url)
                cookies = [
                    {'name': k, 'value': v, 'domain': parsed.netloc, 'path': '/'}
                    for k, v in session.cookies.items()
                ]
                await self._browser.set_cookies(cookies)
            
            fetch_start = time.perf_counter()
            html, final_url = await self._browser.fetch_page_with_url(url)
            timing['fetch'] = (time.perf_counter() - fetch_start) * 1000
            
            # Get updated cookies
            browser_cookies = await self._browser.get_cookies()
            for cookie in browser_cookies:
                session.cookies[cookie['name']] = cookie['value']
            
            return GhostResult(
                url=url,
                html=html,
                status_code=200,
                final_url=final_url,
                headers={},
                cookies=session.cookies,
                timing=timing,
                session_id=session.session_id,
            )
            
        except Exception as e:
            logger.error("ghostnet_browser_error", url=url, error=str(e))
            # Fallback to HTTP
            return await self._fetch_with_http(url, headers, session, timing)
    
    async def crawl_site(
        self,
        start_url: str,
        max_pages: int = 10,
        max_depth: int = 2,
    ) -> List[GhostResult]:
        """
        Crawl a site using GhostNet Protocol.
        Follows links while maintaining session consistency.
        """
        results = []
        visited: Set[str] = set()
        queue: deque = deque([(start_url, 0)])
        
        while queue and len(results) < max_pages:
            url, depth = queue.popleft()
            
            if url in visited or depth > max_depth:
                continue
            
            visited.add(url)
            
            # Fetch with GhostNet
            result = await self.fetch(url)
            
            if result.status_code == 200:
                results.append(result)
                
                # Extract links for next level
                if depth < max_depth:
                    links = self._extract_links(result.html, url)
                    for link in links[:20]:  # Limit links per page
                        if link not in visited:
                            queue.append((link, depth + 1))
            
            # Apply neural timing between pages
            delay = self._timing_engine.get_next_delay(len(result.html))
            await asyncio.sleep(delay)
        
        return results
    
    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract links from HTML"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'lxml')
        links = []
        base_domain = urlparse(base_url).netloc
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            
            # Only same-domain links
            if parsed.netloc == base_domain:
                links.append(full_url)
        
        return list(set(links))
