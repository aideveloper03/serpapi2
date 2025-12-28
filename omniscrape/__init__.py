"""
OmniScrape Engine
=================

Production-ready, high-volume web and search engine scraping API.

Features:
- Multi-engine search (Google, Bing, DuckDuckGo, Yahoo, Yandex)
- Deep web crawling with content extraction
- Anti-detection suite (fingerprinting, proxies, CAPTCHA)
- GhostNet Protocol for maximum stealth
- Data mining and contact extraction

Usage:
    from omniscrape import app
    
    # Run with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

__version__ = "1.0.0"
__author__ = "OmniScrape Team"

from .main import app

__all__ = ["app", "__version__"]
