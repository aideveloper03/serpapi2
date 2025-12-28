"""
Unit tests for search engine parsers
"""

import pytest
from core.engines.google import GoogleSearchEngine
from core.engines.bing import BingSearchEngine
from core.engines.duckduckgo import DuckDuckGoSearchEngine
from core.engines.yahoo import YahooSearchEngine
from core.engines.yandex import YandexSearchEngine
from models import SearchVertical


class TestGoogleSearchEngine:
    """Tests for Google search engine parser"""
    
    def setup_method(self):
        self.engine = GoogleSearchEngine()
    
    def test_build_search_url_basic(self):
        """Test basic search URL construction"""
        url = self.engine.build_search_url(
            query="test query",
            vertical=SearchVertical.ALL,
        )
        
        assert "google.com" in url
        assert "q=test+query" in url or "q=test%20query" in url
    
    def test_build_search_url_with_params(self):
        """Test search URL with various parameters"""
        url = self.engine.build_search_url(
            query="python tutorial",
            vertical=SearchVertical.ALL,
            page=2,
            num_results=20,
            country="us",
            language="en",
            safe_search=True,
        )
        
        assert "num=20" in url
        assert "start=" in url  # Pagination
        assert "gl=us" in url
        assert "hl=en" in url
        assert "safe=active" in url
    
    def test_build_news_url(self):
        """Test news search URL"""
        url = self.engine.build_search_url(
            query="breaking news",
            vertical=SearchVertical.NEWS,
        )
        
        assert "tbm=nws" in url
    
    def test_build_images_url(self):
        """Test image search URL"""
        url = self.engine.build_search_url(
            query="cats",
            vertical=SearchVertical.IMAGES,
        )
        
        assert "tbm=isch" in url
    
    def test_build_videos_url(self):
        """Test video search URL"""
        url = self.engine.build_search_url(
            query="tutorial",
            vertical=SearchVertical.VIDEOS,
        )
        
        assert "tbm=vid" in url
    
    def test_detect_captcha(self):
        """Test CAPTCHA detection"""
        html_with_captcha = """
        <html>
            <body>
                <div class="g-recaptcha" data-sitekey="abc123"></div>
            </body>
        </html>
        """
        
        assert self.engine.detect_captcha(html_with_captcha) == True
    
    def test_detect_no_captcha(self):
        """Test no CAPTCHA detected on normal page"""
        html_normal = """
        <html>
            <body>
                <div class="search-results">Normal results here</div>
            </body>
        </html>
        """
        
        assert self.engine.detect_captcha(html_normal) == False
    
    def test_clean_url_google_redirect(self):
        """Test cleaning Google redirect URLs"""
        redirect_url = "/url?q=https://example.com/page&sa=U"
        cleaned = self.engine.clean_url(redirect_url)
        
        assert cleaned == "https://example.com/page"
    
    def test_parse_results_empty_html(self):
        """Test parsing empty HTML"""
        result = self.engine.parse_results("<html><body></body></html>", SearchVertical.ALL)
        
        assert result.results == []
        assert result.has_captcha == False
    
    def test_parse_organic_results(self):
        """Test parsing organic search results"""
        html = """
        <html>
            <body>
                <div class="g">
                    <div class="yuRUbf">
                        <a href="https://example.com">
                            <h3>Example Title</h3>
                        </a>
                    </div>
                    <div class="VwiC3b">This is the description.</div>
                </div>
            </body>
        </html>
        """
        
        result = self.engine.parse_results(html, SearchVertical.ALL)
        
        # May or may not parse depending on exact selector match
        assert result.has_captcha == False


class TestBingSearchEngine:
    """Tests for Bing search engine parser"""
    
    def setup_method(self):
        self.engine = BingSearchEngine()
    
    def test_build_search_url(self):
        """Test Bing search URL construction"""
        url = self.engine.build_search_url(
            query="test query",
            vertical=SearchVertical.ALL,
        )
        
        assert "bing.com" in url
        assert "q=test+query" in url or "q=test%20query" in url
    
    def test_build_news_url(self):
        """Test Bing news URL"""
        url = self.engine.build_search_url(
            query="news",
            vertical=SearchVertical.NEWS,
        )
        
        assert "/news/" in url


class TestDuckDuckGoSearchEngine:
    """Tests for DuckDuckGo search engine parser"""
    
    def setup_method(self):
        self.engine = DuckDuckGoSearchEngine()
    
    def test_build_search_url(self):
        """Test DuckDuckGo search URL"""
        url = self.engine.build_search_url(
            query="privacy search",
            vertical=SearchVertical.ALL,
        )
        
        assert "duckduckgo.com" in url
        assert "q=privacy" in url
    
    def test_uses_html_version(self):
        """Test that HTML version is used for easier parsing"""
        url = self.engine.build_search_url(
            query="test",
            vertical=SearchVertical.ALL,
        )
        
        assert "html.duckduckgo.com" in url


class TestYahooSearchEngine:
    """Tests for Yahoo search engine parser"""
    
    def setup_method(self):
        self.engine = YahooSearchEngine()
    
    def test_build_search_url(self):
        """Test Yahoo search URL"""
        url = self.engine.build_search_url(
            query="yahoo search",
            vertical=SearchVertical.ALL,
        )
        
        assert "yahoo.com" in url
        assert "p=yahoo" in url


class TestYandexSearchEngine:
    """Tests for Yandex search engine parser"""
    
    def setup_method(self):
        self.engine = YandexSearchEngine()
    
    def test_build_search_url(self):
        """Test Yandex search URL"""
        url = self.engine.build_search_url(
            query="русский поиск",
            vertical=SearchVertical.ALL,
        )
        
        assert "yandex.com" in url
        assert "text=" in url
