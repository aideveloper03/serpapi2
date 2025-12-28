"""
Pytest configuration and fixtures
"""

import pytest
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_html():
    """Sample HTML for testing parsers"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="description" content="Sample page for testing">
        <meta property="og:title" content="Sample OG Title">
        <meta property="og:description" content="Sample OG Description">
        <title>Sample Page Title</title>
        <script type="application/ld+json">
        {
            "@type": "Article",
            "headline": "Sample Article",
            "author": {"@type": "Person", "name": "Test Author"}
        }
        </script>
    </head>
    <body>
        <nav>Navigation Menu</nav>
        <article>
            <h1>Main Article Title</h1>
            <p>This is the first paragraph with enough content to be considered meaningful text for extraction purposes.</p>
            <p>This is the second paragraph providing additional context and information about the topic being discussed.</p>
            <p>Contact: contact@example.com | Phone: (555) 123-4567</p>
            <a href="https://twitter.com/example">Follow us on Twitter</a>
        </article>
        <footer>
            <p>Footer content</p>
            <a href="mailto:info@example.com">Email us</a>
        </footer>
    </body>
    </html>
    """


@pytest.fixture
def sample_search_html():
    """Sample search results HTML"""
    return """
    <html>
    <body>
        <div class="g">
            <div class="yuRUbf">
                <a href="https://result1.com">
                    <h3>First Result Title</h3>
                </a>
            </div>
            <div class="VwiC3b">Description for first result.</div>
        </div>
        <div class="g">
            <div class="yuRUbf">
                <a href="https://result2.com">
                    <h3>Second Result Title</h3>
                </a>
            </div>
            <div class="VwiC3b">Description for second result.</div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def mock_proxy():
    """Mock proxy for testing"""
    from services.proxy_manager import Proxy
    return Proxy(
        host="127.0.0.1",
        port=8080,
        protocol="http",
    )
