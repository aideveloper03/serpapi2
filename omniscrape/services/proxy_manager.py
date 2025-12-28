"""
OmniScrape Engine - Proxy Manager
High-performance proxy rotation, validation, and management
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse
import httpx

from config import settings
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class ProxyStats:
    """Statistics for a proxy"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    last_used: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    blocked_domains: Set[str] = field(default_factory=set)
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def avg_latency_ms(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests


@dataclass
class Proxy:
    """Proxy configuration"""
    host: str
    port: int
    protocol: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    stats: ProxyStats = field(default_factory=ProxyStats)
    
    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if proxy is considered healthy"""
        # Mark unhealthy if too many consecutive failures
        if self.stats.consecutive_failures >= 5:
            return False
        # Mark unhealthy if success rate is too low (after enough requests)
        if self.stats.total_requests >= 10 and self.stats.success_rate < 0.3:
            return False
        return True
    
    def record_success(self, latency_ms: float) -> None:
        """Record a successful request"""
        self.stats.total_requests += 1
        self.stats.successful_requests += 1
        self.stats.total_latency_ms += latency_ms
        self.stats.last_used = datetime.utcnow()
        self.stats.last_success = datetime.utcnow()
        self.stats.consecutive_failures = 0
    
    def record_failure(self, domain: Optional[str] = None) -> None:
        """Record a failed request"""
        self.stats.total_requests += 1
        self.stats.failed_requests += 1
        self.stats.last_used = datetime.utcnow()
        self.stats.last_failure = datetime.utcnow()
        self.stats.consecutive_failures += 1
        if domain:
            self.stats.blocked_domains.add(domain)


class ProxyManager:
    """
    High-performance proxy manager with:
    - Real-time proxy list fetching and validation
    - Intelligent rotation based on success rates
    - Per-domain blocking detection
    - Latency-based prioritization
    """
    
    # Public proxy list sources
    PROXY_SOURCES = [
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
    ]
    
    VALIDATION_URL = "http://httpbin.org/ip"
    VALIDATION_TIMEOUT = 5.0
    
    def __init__(
        self,
        pool_size: int = 50,
        validation_timeout: float = 5.0,
        rotation_interval: int = 30,
    ):
        self.pool_size = pool_size
        self.validation_timeout = validation_timeout
        self.rotation_interval = rotation_interval
        
        self._proxies: Dict[str, Proxy] = {}
        self._custom_proxies: Dict[str, Proxy] = {}
        self._lock = asyncio.Lock()
        self._last_refresh: Optional[datetime] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._validation_semaphore = asyncio.Semaphore(20)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the proxy pool"""
        if self._initialized:
            return
        
        logger.info("proxy_manager_initializing", pool_size=self.pool_size)
        
        # Add custom proxy if configured
        if settings.custom_proxy_url:
            await self.add_custom_proxy(settings.custom_proxy_url)
        
        # Fetch and validate public proxies
        await self.refresh_pool()
        
        self._initialized = True
        logger.info(
            "proxy_manager_initialized",
            active_proxies=len(self._proxies),
            custom_proxies=len(self._custom_proxies),
        )
    
    async def add_custom_proxy(self, proxy_url: str) -> bool:
        """Add a custom proxy to the pool"""
        try:
            parsed = urlparse(proxy_url)
            proxy = Proxy(
                host=parsed.hostname or "",
                port=parsed.port or 80,
                protocol=parsed.scheme or "http",
                username=parsed.username,
                password=parsed.password,
            )
            
            if await self._validate_proxy(proxy):
                self._custom_proxies[proxy.url] = proxy
                logger.info("custom_proxy_added", proxy=f"{proxy.host}:{proxy.port}")
                return True
            return False
        except Exception as e:
            logger.error("custom_proxy_add_failed", error=str(e))
            return False
    
    async def refresh_pool(self) -> None:
        """Refresh the proxy pool from public sources"""
        async with self._lock:
            all_proxies: List[str] = []
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                for source in self.PROXY_SOURCES:
                    try:
                        response = await client.get(source)
                        if response.status_code == 200:
                            lines = response.text.strip().split("\n")
                            all_proxies.extend(lines)
                            logger.debug(
                                "proxy_source_fetched",
                                source=source,
                                count=len(lines),
                            )
                    except Exception as e:
                        logger.warning(
                            "proxy_source_fetch_failed",
                            source=source,
                            error=str(e),
                        )
            
            # Deduplicate and parse
            unique_proxies: Set[str] = set()
            parsed_proxies: List[Proxy] = []
            
            for proxy_str in all_proxies:
                proxy_str = proxy_str.strip()
                if not proxy_str or proxy_str in unique_proxies:
                    continue
                
                unique_proxies.add(proxy_str)
                
                try:
                    if ":" in proxy_str:
                        parts = proxy_str.split(":")
                        if len(parts) >= 2:
                            host, port = parts[0], int(parts[1])
                            parsed_proxies.append(Proxy(host=host, port=port))
                except (ValueError, IndexError):
                    continue
            
            logger.info(
                "proxy_pool_parsed",
                total=len(all_proxies),
                unique=len(parsed_proxies),
            )
            
            # Validate a sample
            sample_size = min(len(parsed_proxies), self.pool_size * 3)
            sample = random.sample(parsed_proxies, sample_size) if parsed_proxies else []
            
            validated = await self._validate_proxies(sample)
            
            # Keep top performers
            for proxy in validated[:self.pool_size]:
                self._proxies[proxy.url] = proxy
            
            self._last_refresh = datetime.utcnow()
            logger.info(
                "proxy_pool_refreshed",
                validated=len(validated),
                active=len(self._proxies),
            )
    
    async def _validate_proxies(self, proxies: List[Proxy]) -> List[Proxy]:
        """Validate multiple proxies concurrently"""
        tasks = [self._validate_proxy(proxy) for proxy in proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        validated = []
        for proxy, result in zip(proxies, results):
            if result is True:
                validated.append(proxy)
        
        # Sort by latency
        validated.sort(key=lambda p: p.stats.avg_latency_ms if p.stats.avg_latency_ms > 0 else float('inf'))
        return validated
    
    async def _validate_proxy(self, proxy: Proxy) -> bool:
        """Validate a single proxy"""
        async with self._validation_semaphore:
            try:
                start_time = time.perf_counter()
                
                async with httpx.AsyncClient(
                    proxy=proxy.url,
                    timeout=self.validation_timeout,
                ) as client:
                    response = await client.get(self.VALIDATION_URL)
                    
                    if response.status_code == 200:
                        latency = (time.perf_counter() - start_time) * 1000
                        proxy.record_success(latency)
                        return True
                    
                    proxy.record_failure()
                    return False
                    
            except Exception:
                proxy.record_failure()
                return False
    
    def get_proxy(self, domain: Optional[str] = None) -> Optional[Proxy]:
        """Get the best available proxy"""
        # Prefer custom proxies
        if self._custom_proxies:
            candidates = [
                p for p in self._custom_proxies.values()
                if p.is_healthy and (not domain or domain not in p.stats.blocked_domains)
            ]
            if candidates:
                return self._select_best(candidates)
        
        # Fall back to public proxies
        candidates = [
            p for p in self._proxies.values()
            if p.is_healthy and (not domain or domain not in p.stats.blocked_domains)
        ]
        
        if not candidates:
            # If no healthy proxies, try any proxy
            candidates = list(self._proxies.values())
        
        if candidates:
            return self._select_best(candidates)
        
        return None
    
    def _select_best(self, candidates: List[Proxy]) -> Proxy:
        """Select the best proxy using weighted random selection"""
        if not candidates:
            raise ValueError("No candidates provided")
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Weight by success rate and inverse latency
        weights = []
        for proxy in candidates:
            success_weight = proxy.stats.success_rate * 100
            latency_weight = max(1, 100 - proxy.stats.avg_latency_ms / 10)
            
            # Bonus for less used proxies
            recency_weight = 1.0
            if proxy.stats.last_used:
                seconds_ago = (datetime.utcnow() - proxy.stats.last_used).total_seconds()
                if seconds_ago > 60:
                    recency_weight = 1.5
            
            weights.append(success_weight * latency_weight * recency_weight)
        
        # Weighted random selection
        total = sum(weights)
        if total == 0:
            return random.choice(candidates)
        
        r = random.uniform(0, total)
        cumulative = 0
        for proxy, weight in zip(candidates, weights):
            cumulative += weight
            if r <= cumulative:
                return proxy
        
        return candidates[-1]
    
    def get_proxy_url(self, domain: Optional[str] = None) -> Optional[str]:
        """Get proxy URL string"""
        proxy = self.get_proxy(domain)
        return proxy.url if proxy else None
    
    def report_success(self, proxy_url: str, latency_ms: float) -> None:
        """Report a successful request through a proxy"""
        proxy = self._proxies.get(proxy_url) or self._custom_proxies.get(proxy_url)
        if proxy:
            proxy.record_success(latency_ms)
    
    def report_failure(self, proxy_url: str, domain: Optional[str] = None) -> None:
        """Report a failed request through a proxy"""
        proxy = self._proxies.get(proxy_url) or self._custom_proxies.get(proxy_url)
        if proxy:
            proxy.record_failure(domain)
    
    def get_spoof_headers(self) -> Dict[str, str]:
        """Get IP spoofing headers"""
        fake_ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        
        return {
            "X-Forwarded-For": fake_ip,
            "X-Real-IP": fake_ip,
            "Via": f"1.1 {fake_ip}",
            "Forwarded": f"for={fake_ip}",
            "X-Originating-IP": fake_ip,
            "X-Client-IP": fake_ip,
        }
    
    @property
    def pool_size_current(self) -> int:
        """Get current pool size"""
        return len(self._proxies) + len(self._custom_proxies)
    
    @property
    def healthy_proxy_count(self) -> int:
        """Get count of healthy proxies"""
        return sum(
            1 for p in list(self._proxies.values()) + list(self._custom_proxies.values())
            if p.is_healthy
        )
    
    def get_stats(self) -> Dict:
        """Get proxy pool statistics"""
        all_proxies = list(self._proxies.values()) + list(self._custom_proxies.values())
        
        if not all_proxies:
            return {
                "total": 0,
                "healthy": 0,
                "avg_success_rate": 0,
                "avg_latency_ms": 0,
            }
        
        healthy = [p for p in all_proxies if p.is_healthy]
        
        avg_success = sum(p.stats.success_rate for p in all_proxies) / len(all_proxies)
        latencies = [p.stats.avg_latency_ms for p in all_proxies if p.stats.avg_latency_ms > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        return {
            "total": len(all_proxies),
            "healthy": len(healthy),
            "custom": len(self._custom_proxies),
            "avg_success_rate": round(avg_success, 3),
            "avg_latency_ms": round(avg_latency, 2),
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
        }


# Singleton instance
proxy_manager = ProxyManager(
    pool_size=settings.proxy_pool_size,
    validation_timeout=settings.proxy_validation_timeout,
    rotation_interval=settings.proxy_rotation_interval,
)
