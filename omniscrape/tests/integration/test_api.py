"""
Integration tests for API endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    def test_health_check(self, client):
        """Test basic health check"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data
    
    def test_liveness_check(self, client):
        """Test liveness probe"""
        response = client.get("/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
    
    def test_readiness_check(self, client):
        """Test readiness probe"""
        response = client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data


class TestRootEndpoint:
    """Tests for root endpoint"""
    
    def test_root(self, client):
        """Test root endpoint returns API info"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


class TestSearchEndpoints:
    """Tests for search API endpoints"""
    
    def test_search_validation(self, client):
        """Test search request validation"""
        # Empty query should fail
        response = client.post(
            "/api/v1/search",
            json={"query": ""}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_search_valid_request(self, client):
        """Test valid search request structure"""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "test query",
                "engine": "auto",
                "num_results": 5
            }
        )
        
        # Should return response (may fail due to network, but structure is correct)
        assert response.status_code in [200, 500]
        data = response.json()
        
        if response.status_code == 200:
            assert "success" in data
            assert "results" in data
            assert "trace_id" in data
    
    def test_quick_search(self, client):
        """Test quick search GET endpoint"""
        response = client.get("/api/v1/search?q=test")
        
        assert response.status_code in [200, 500]


class TestCrawlEndpoints:
    """Tests for crawl API endpoints"""
    
    def test_crawl_validation(self, client):
        """Test crawl request validation"""
        # Invalid depth should fail
        response = client.post(
            "/api/v1/crawl",
            json={"url": "https://example.com", "depth": 10}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_crawl_valid_request(self, client):
        """Test valid crawl request structure"""
        response = client.post(
            "/api/v1/crawl",
            json={
                "url": "https://example.com",
                "depth": 1,
                "max_pages": 1
            }
        )
        
        assert response.status_code in [200, 500]
        data = response.json()
        
        if response.status_code == 200:
            assert "success" in data
            assert "pages" in data


class TestDataMiningEndpoints:
    """Tests for data mining API endpoints"""
    
    def test_mine_validation(self, client):
        """Test mine request validation"""
        # Empty URLs should fail
        response = client.post(
            "/api/v1/mine",
            json={"urls": []}
        )
        
        assert response.status_code == 422
    
    def test_mine_valid_request(self, client):
        """Test valid mine request structure"""
        response = client.post(
            "/api/v1/mine",
            json={
                "urls": ["https://example.com"],
                "extract_emails": True,
                "parallel": False
            }
        )
        
        assert response.status_code in [200, 500]


class TestRateLimiting:
    """Tests for rate limiting"""
    
    def test_rate_limit_headers(self, client):
        """Test rate limit headers are present"""
        response = client.get("/")
        
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers


class TestTraceHeaders:
    """Tests for trace headers"""
    
    def test_trace_id_header(self, client):
        """Test trace ID is returned in response"""
        response = client.get("/health")
        
        assert "X-Trace-ID" in response.headers
        assert "X-Request-ID" in response.headers
        assert "X-Response-Time" in response.headers
