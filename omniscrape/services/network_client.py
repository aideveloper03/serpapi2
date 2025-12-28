"""
OmniScrape Engine - Network Client
High-performance HTTP client with TLS fingerprinting and anti-detection
"""

import asyncio
import random
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings
from utils import get_logger
from .proxy_manager import proxy_manager

logger = get_logger(__name__)


class BrowserProfile(Enum):
    """Browser TLS fingerprint profiles"""
    CHROME_120 = "chrome120"
    CHROME_119 = "chrome119"
    CHROME_118 = "chrome118"
    FIREFOX_121 = "firefox121"
    FIREFOX_120 = "firefox120"
    SAFARI_17 = "safari17"
    EDGE_120 = "edge120"


@dataclass
class UserAgentProfile:
    """Complete browser profile including UA and headers"""
    user_agent: str
    sec_ch_ua: str
    sec_ch_ua_mobile: str
    sec_ch_ua_platform: str
    accept_language: str
    accept: str
    accept_encoding: str
    
    def to_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Sec-Ch-Ua": self.sec_ch_ua,
            "Sec-Ch-Ua-Mobile": self.sec_ch_ua_mobile,
            "Sec-Ch-Ua-Platform": self.sec_ch_ua_platform,
            "Accept-Language": self.accept_language,
            "Accept": self.accept,
            "Accept-Encoding": self.accept_encoding,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }


class FingerprintRotator:
    """
    Rotates browser fingerprints to avoid detection
    Includes realistic User-Agent strings and associated headers
    """
    
    PROFILES: List[UserAgentProfile] = [
        # Chrome 120 on Windows
        UserAgentProfile(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            sec_ch_ua_mobile="?0",
            sec_ch_ua_platform='"Windows"',
            accept_language="en-US,en;q=0.9",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            accept_encoding="gzip, deflate, br",
        ),
        # Chrome 120 on macOS
        UserAgentProfile(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            sec_ch_ua_mobile="?0",
            sec_ch_ua_platform='"macOS"',
            accept_language="en-US,en;q=0.9",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            accept_encoding="gzip, deflate, br",
        ),
        # Chrome 119 on Windows
        UserAgentProfile(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            sec_ch_ua='"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            sec_ch_ua_mobile="?0",
            sec_ch_ua_platform='"Windows"',
            accept_language="en-US,en;q=0.9,de;q=0.8",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            accept_encoding="gzip, deflate, br",
        ),
        # Firefox 121 on Windows
        UserAgentProfile(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            sec_ch_ua="",
            sec_ch_ua_mobile="",
            sec_ch_ua_platform="",
            accept_language="en-US,en;q=0.5",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            accept_encoding="gzip, deflate, br",
        ),
        # Firefox 120 on macOS
        UserAgentProfile(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
            sec_ch_ua="",
            sec_ch_ua_mobile="",
            sec_ch_ua_platform="",
            accept_language="en-US,en;q=0.5",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            accept_encoding="gzip, deflate, br",
        ),
        # Safari 17 on macOS
        UserAgentProfile(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            sec_ch_ua="",
            sec_ch_ua_mobile="",
            sec_ch_ua_platform="",
            accept_language="en-US,en;q=0.9",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            accept_encoding="gzip, deflate, br",
        ),
        # Edge 120 on Windows
        UserAgentProfile(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
            sec_ch_ua_mobile="?0",
            sec_ch_ua_platform='"Windows"',
            accept_language="en-US,en;q=0.9",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            accept_encoding="gzip, deflate, br",
        ),
        # Chrome on Linux
        UserAgentProfile(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            sec_ch_ua_mobile="?0",
            sec_ch_ua_platform='"Linux"',
            accept_language="en-US,en;q=0.9",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            accept_encoding="gzip, deflate, br",
        ),
        # Mobile Chrome
        UserAgentProfile(
            user_agent="Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            sec_ch_ua_mobile="?1",
            sec_ch_ua_platform='"Android"',
            accept_language="en-US,en;q=0.9",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            accept_encoding="gzip, deflate, br",
        ),
    ]
    
    def __init__(self):
        self._current_profile: Optional[UserAgentProfile] = None
        self._profile_used_count = 0
        self._max_uses_per_profile = random.randint(5, 15)
    
    def get_profile(self) -> UserAgentProfile:
        """Get a fingerprint profile with rotation"""
        if self._current_profile is None or self._profile_used_count >= self._max_uses_per_profile:
            self._current_profile = random.choice(self.PROFILES)
            self._profile_used_count = 0
            self._max_uses_per_profile = random.randint(5, 15)
        
        self._profile_used_count += 1
        return self._current_profile
    
    def get_random_profile(self) -> UserAgentProfile:
        """Get a random profile without rotation logic"""
        return random.choice(self.PROFILES)


class CookieJar:
    """
    Manages cookies across sessions to appear more human-like
    Maintains realistic session cookies for different domains
    """
    
    def __init__(self):
        self._cookies: Dict[str, Dict[str, str]] = {}
        self._session_ids: Dict[str, str] = {}
    
    def _generate_session_id(self) -> str:
        """Generate a realistic session ID"""
        import hashlib
        import secrets
        return hashlib.md5(secrets.token_bytes(32)).hexdigest()
    
    def get_cookies(self, domain: str) -> Dict[str, str]:
        """Get cookies for a domain"""
        if domain not in self._cookies:
            self._cookies[domain] = self._generate_cookies(domain)
        return self._cookies[domain]
    
    def _generate_cookies(self, domain: str) -> Dict[str, str]:
        """Generate realistic cookies for a domain"""
        base_cookies = {}
        
        # Generate session ID
        session_id = self._generate_session_id()
        self._session_ids[domain] = session_id
        
        # Common cookie patterns
        if "google" in domain:
            base_cookies.update({
                "CONSENT": f"YES+cb.{random.randint(10000, 99999)}-17-p0.en+FX+{random.randint(100, 999)}",
                "SOCS": "CAESHAgBEhJnd3NfMjAyMzEwMDUtMF9SQzEaAmVuIAEaBgiA_9CqBg",
                "NID": f"{random.randint(100, 999)}=",
            })
        elif "bing" in domain:
            base_cookies.update({
                "MUID": f"{secrets.token_hex(16).upper()}",
                "SRCHD": "AF=NOFORM",
                "SRCHUID": f"V=2&GUID={secrets.token_hex(16).upper()}&dmnchg=1",
            })
        elif "duckduckgo" in domain:
            base_cookies.update({
                "ae": "d",
                "ax": "v408-1",
            })
        
        return base_cookies
    
    def update_cookies(self, domain: str, cookies: Dict[str, str]) -> None:
        """Update cookies for a domain"""
        if domain not in self._cookies:
            self._cookies[domain] = {}
        self._cookies[domain].update(cookies)
    
    def clear_domain(self, domain: str) -> None:
        """Clear cookies for a domain"""
        self._cookies.pop(domain, None)
        self._session_ids.pop(domain, None)


class NetworkClient:
    """
    High-performance HTTP client with comprehensive anti-detection features:
    - TLS fingerprint mimicking via curl-cffi
    - Automatic proxy rotation
    - Browser fingerprint rotation
    - Cookie management
    - Retry logic with exponential backoff
    """
    
    def __init__(
        self,
        use_proxy: bool = True,
        use_fingerprint: bool = True,
        use_cookies: bool = True,
    ):
        self.use_proxy = use_proxy
        self.use_fingerprint = use_fingerprint
        self.use_cookies = use_cookies
        
        self._fingerprint_rotator = FingerprintRotator()
        self._cookie_jar = CookieJar()
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_serp_scrapes)
        
        # Try to import curl_cffi for TLS fingerprinting
        self._curl_available = False
        try:
            from curl_cffi.requests import AsyncSession
            self._curl_available = True
            logger.info("curl_cffi_available", tls_fingerprinting=True)
        except ImportError:
            logger.warning("curl_cffi_not_available", tls_fingerprinting=False)
    
    async def _get_httpx_client(
        self,
        proxy_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> httpx.AsyncClient:
        """Create an httpx client with optional proxy"""
        return httpx.AsyncClient(
            proxy=proxy_url,
            timeout=httpx.Timeout(timeout),
            http2=True,
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
            ),
        )
    
    def _build_headers(
        self,
        domain: str,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Build request headers with fingerprinting"""
        headers = {}
        
        # Add browser fingerprint
        if self.use_fingerprint:
            profile = self._fingerprint_rotator.get_profile()
            headers.update(profile.to_headers())
        
        # Add IP spoofing headers
        if self.use_proxy:
            headers.update(proxy_manager.get_spoof_headers())
        
        # Add referer for non-direct navigation
        if random.random() > 0.3:
            referrers = [
                "https://www.google.com/",
                "https://www.bing.com/",
                "https://duckduckgo.com/",
                f"https://{domain}/",
            ]
            headers["Referer"] = random.choice(referrers)
        
        # Add custom headers
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        use_curl: bool = False,
        browser_profile: Optional[BrowserProfile] = None,
    ) -> Tuple[int, str, Dict[str, str]]:
        """
        Make an HTTP request with anti-detection features
        
        Returns:
            Tuple of (status_code, response_text, response_headers)
        """
        from urllib.parse import urlparse
        
        async with self._semaphore:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # Build headers
            request_headers = self._build_headers(domain, headers)
            
            # Get cookies
            if self.use_cookies:
                cookies = self._cookie_jar.get_cookies(domain)
            else:
                cookies = {}
            
            # Get proxy
            proxy_url = None
            if self.use_proxy:
                proxy_url = proxy_manager.get_proxy_url(domain)
            
            start_time = time.perf_counter()
            
            try:
                # Use curl_cffi for TLS fingerprinting if available and requested
                if use_curl and self._curl_available:
                    status, text, resp_headers = await self._curl_request(
                        method=method,
                        url=url,
                        headers=request_headers,
                        data=data,
                        json_data=json,
                        params=params,
                        proxy=proxy_url,
                        timeout=timeout,
                        browser=browser_profile,
                    )
                else:
                    # Use httpx
                    status, text, resp_headers = await self._httpx_request(
                        method=method,
                        url=url,
                        headers=request_headers,
                        data=data,
                        json_data=json,
                        params=params,
                        cookies=cookies,
                        proxy=proxy_url,
                        timeout=timeout,
                    )
                
                # Record success
                latency = (time.perf_counter() - start_time) * 1000
                if proxy_url:
                    proxy_manager.report_success(proxy_url, latency)
                
                logger.debug(
                    "request_success",
                    url=url,
                    status=status,
                    latency_ms=round(latency, 2),
                    proxy_used=proxy_url is not None,
                )
                
                return status, text, resp_headers
                
            except Exception as e:
                # Record failure
                if proxy_url:
                    proxy_manager.report_failure(proxy_url, domain)
                
                logger.error(
                    "request_failed",
                    url=url,
                    error=str(e),
                    proxy_used=proxy_url is not None,
                )
                raise
    
    async def _httpx_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Optional[Dict[str, Any]],
        json_data: Optional[Dict[str, Any]],
        params: Optional[Dict[str, str]],
        cookies: Dict[str, str],
        proxy: Optional[str],
        timeout: float,
    ) -> Tuple[int, str, Dict[str, str]]:
        """Make request using httpx"""
        async with await self._get_httpx_client(proxy, timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json_data,
                params=params,
                cookies=cookies,
            )
            
            return (
                response.status_code,
                response.text,
                dict(response.headers),
            )
    
    async def _curl_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Optional[Dict[str, Any]],
        json_data: Optional[Dict[str, Any]],
        params: Optional[Dict[str, str]],
        proxy: Optional[str],
        timeout: float,
        browser: Optional[BrowserProfile],
    ) -> Tuple[int, str, Dict[str, str]]:
        """Make request using curl_cffi with TLS fingerprinting"""
        from curl_cffi.requests import AsyncSession
        
        # Map browser profile to curl_cffi impersonate
        impersonate_map = {
            BrowserProfile.CHROME_120: "chrome120",
            BrowserProfile.CHROME_119: "chrome119",
            BrowserProfile.CHROME_118: "chrome118",
            BrowserProfile.FIREFOX_121: "firefox121",
            BrowserProfile.FIREFOX_120: "firefox120",
            BrowserProfile.SAFARI_17: "safari17",
            BrowserProfile.EDGE_120: "edge120",
        }
        
        impersonate = impersonate_map.get(browser, "chrome120")
        
        async with AsyncSession(impersonate=impersonate) as session:
            response = await session.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json_data,
                params=params,
                proxy=proxy,
                timeout=timeout,
            )
            
            return (
                response.status_code,
                response.text,
                dict(response.headers),
            )
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        use_curl: bool = False,
    ) -> Tuple[int, str, Dict[str, str]]:
        """Convenience method for GET requests"""
        return await self.request(
            method="GET",
            url=url,
            headers=headers,
            params=params,
            timeout=timeout,
            use_curl=use_curl,
        )
    
    async def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        use_curl: bool = False,
    ) -> Tuple[int, str, Dict[str, str]]:
        """Convenience method for POST requests"""
        return await self.request(
            method="POST",
            url=url,
            headers=headers,
            data=data,
            json=json,
            timeout=timeout,
            use_curl=use_curl,
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def get_with_retry(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ) -> Tuple[int, str, Dict[str, str]]:
        """GET request with automatic retry"""
        return await self.get(url, headers, params, timeout)
    
    def update_cookies(self, domain: str, cookies: Dict[str, str]) -> None:
        """Update cookies for a domain"""
        self._cookie_jar.update_cookies(domain, cookies)
    
    def clear_cookies(self, domain: Optional[str] = None) -> None:
        """Clear cookies for a domain or all domains"""
        if domain:
            self._cookie_jar.clear_domain(domain)
        else:
            self._cookie_jar = CookieJar()


# Default client instance
network_client = NetworkClient(
    use_proxy=settings.rotate_user_agent,
    use_fingerprint=settings.rotate_fingerprint,
    use_cookies=True,
)


# Import secrets for cookie generation
import secrets
