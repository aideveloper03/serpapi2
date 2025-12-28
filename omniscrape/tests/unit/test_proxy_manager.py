"""
Unit tests for proxy manager
"""

import pytest
from services.proxy_manager import Proxy, ProxyStats, ProxyManager


class TestProxy:
    """Tests for Proxy dataclass"""
    
    def test_proxy_url_without_auth(self):
        """Test proxy URL generation without authentication"""
        proxy = Proxy(host="192.168.1.1", port=8080)
        
        assert proxy.url == "http://192.168.1.1:8080"
    
    def test_proxy_url_with_auth(self):
        """Test proxy URL generation with authentication"""
        proxy = Proxy(
            host="192.168.1.1",
            port=8080,
            username="user",
            password="pass",
        )
        
        assert proxy.url == "http://user:pass@192.168.1.1:8080"
    
    def test_proxy_url_with_protocol(self):
        """Test proxy URL with different protocol"""
        proxy = Proxy(host="192.168.1.1", port=1080, protocol="socks5")
        
        assert proxy.url == "socks5://192.168.1.1:1080"
    
    def test_proxy_is_healthy_initial(self):
        """Test proxy is healthy initially"""
        proxy = Proxy(host="192.168.1.1", port=8080)
        
        assert proxy.is_healthy == True
    
    def test_proxy_unhealthy_after_failures(self):
        """Test proxy becomes unhealthy after consecutive failures"""
        proxy = Proxy(host="192.168.1.1", port=8080)
        
        for _ in range(5):
            proxy.record_failure()
        
        assert proxy.is_healthy == False
    
    def test_proxy_healthy_after_success(self):
        """Test proxy resets failure count after success"""
        proxy = Proxy(host="192.168.1.1", port=8080)
        
        for _ in range(3):
            proxy.record_failure()
        
        proxy.record_success(100.0)
        
        assert proxy.stats.consecutive_failures == 0
        assert proxy.is_healthy == True


class TestProxyStats:
    """Tests for ProxyStats"""
    
    def test_success_rate_initial(self):
        """Test initial success rate is 1.0"""
        stats = ProxyStats()
        
        assert stats.success_rate == 1.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        stats = ProxyStats(
            total_requests=10,
            successful_requests=8,
            failed_requests=2,
        )
        
        assert stats.success_rate == 0.8
    
    def test_avg_latency_calculation(self):
        """Test average latency calculation"""
        stats = ProxyStats(
            successful_requests=4,
            total_latency_ms=400.0,
        )
        
        assert stats.avg_latency_ms == 100.0


class TestProxyManager:
    """Tests for ProxyManager"""
    
    def test_initialization(self):
        """Test proxy manager initialization"""
        manager = ProxyManager(pool_size=10)
        
        assert manager.pool_size == 10
        assert manager.pool_size_current == 0
    
    def test_get_spoof_headers(self):
        """Test IP spoofing headers generation"""
        manager = ProxyManager()
        headers = manager.get_spoof_headers()
        
        assert "X-Forwarded-For" in headers
        assert "X-Real-IP" in headers
        assert "Via" in headers
        assert "Forwarded" in headers
    
    def test_get_stats_empty(self):
        """Test stats with empty pool"""
        manager = ProxyManager()
        stats = manager.get_stats()
        
        assert stats["total"] == 0
        assert stats["healthy"] == 0
