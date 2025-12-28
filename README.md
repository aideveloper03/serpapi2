# OmniScrape Engine

<div align="center">

![OmniScrape Logo](https://img.shields.io/badge/OmniScrape-Engine-blue?style=for-the-badge&logo=python)

**Production-ready, high-volume web and search engine scraping API**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

## 🚀 Features

### Multi-Engine Search
- **5 Search Engines**: Google, Bing, DuckDuckGo, Yahoo, Yandex
- **Cascading Fallback**: Automatic failover between engines
- **Multiple Verticals**: All, News, Images, Videos
- **Zero-Results Guard**: Never return empty when data exists

### Deep Web Crawling
- **Content Extraction**: Automatic article/content parsing
- **Contact Mining**: Emails, phones, social links, addresses
- **Metadata Parsing**: OpenGraph, Twitter Cards, Schema.org
- **Multi-Mode Crawling**: Simple, Deep, Stealth, GhostNet

### Anti-Detection Suite
- **Browser Fingerprinting**: User-Agent, Sec-Ch-Ua rotation
- **TLS Fingerprinting**: Chrome signature mimicking via curl-cffi
- **Proxy Management**: Auto-rotating, validated proxy pool
- **CAPTCHA Handling**: Detection and local solving
- **GhostNet Protocol**: Novel undetectable crawling techniques

### Production Ready
- **High Concurrency**: 60+ SERP scrapes/min, 30+ deep scrapes/min
- **Docker Support**: Complete containerization with Redis
- **Structured Logging**: JSON logging with trace IDs
- **Rate Limiting**: Redis-based request throttling

---

## 📦 Quick Start

### Docker (Recommended)

```bash
cd omniscrape

# Copy environment file
cp .env.example .env

# Build and run
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run
python main.py
```

---

## 🔌 API Endpoints

### Search API

```bash
# Multi-engine search with auto-fallback
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "python web scraping", "engine": "auto"}'

# Quick search
curl "http://localhost:8000/api/v1/search?q=python&num=10"
```

### Crawl API

```bash
# Deep crawl with content extraction
curl -X POST "http://localhost:8000/api/v1/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "depth": 2}'

# Stealth crawl with anti-detection
curl -X POST "http://localhost:8000/api/v1/crawl/stealth" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://protected-site.com"}'
```

### Data Mining API

```bash
# Extract contacts from multiple URLs
curl -X POST "http://localhost:8000/api/v1/mine" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com/contact"], "extract_emails": true}'
```

---

## 🛡️ Anti-Detection Techniques

| Technique | Description |
|-----------|-------------|
| **Browser Fingerprinting** | Rotating User-Agent, Sec-Ch-Ua, and all browser headers |
| **TLS Fingerprinting** | Chrome/Firefox TLS signature mimicking with curl-cffi |
| **Proxy Rotation** | Real-time validated proxy pool with intelligent selection |
| **IP Spoofing** | X-Forwarded-For, Via, and related header manipulation |
| **Canvas/WebGL Spoofing** | Fingerprint randomization in browser mode |
| **CAPTCHA Handling** | Detection and bypass for Cloudflare, reCAPTCHA |
| **GhostNet Protocol** | Novel timing and behavioral mimicking |

---

## 📁 Project Structure

```
omniscrape/
├── api/                    # FastAPI endpoints
│   └── v1/
│       ├── search.py       # Search API
│       ├── crawl.py        # Crawl API
│       ├── data_mining.py  # Data mining API
│       └── health.py       # Health checks
├── core/
│   ├── engines/            # Search engine parsers
│   │   ├── google.py
│   │   ├── bing.py
│   │   ├── duckduckgo.py
│   │   ├── yahoo.py
│   │   ├── yandex.py
│   │   └── orchestrator.py
│   ├── parsers/            # Content extraction
│   │   ├── content_extractor.py
│   │   ├── contact_extractor.py
│   │   └── metadata_extractor.py
│   └── crawlers/           # Web crawlers
│       ├── deep_scraper.py
│       ├── stealth_browser.py
│       └── ghostnet.py
├── services/               # Core services
│   ├── proxy_manager.py
│   ├── network_client.py
│   └── captcha_handler.py
├── middleware/             # FastAPI middleware
├── models/                 # Pydantic schemas
├── config/                 # Configuration
├── utils/                  # Utilities
├── tests/                  # Test suite
├── docs/                   # Documentation
├── main.py                 # Application entry
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## ⚙️ Configuration

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONCURRENT_SERP_SCRAPES` | 60 | Max concurrent search scrapes |
| `MAX_CONCURRENT_DEEP_SCRAPES` | 30 | Max concurrent deep scrapes |
| `PROXY_POOL_SIZE` | 50 | Maximum proxy pool size |
| `STEALTH_MODE` | true | Enable anti-detection features |
| `HEADLESS_MODE` | true | Run browsers headless |
| `REDIS_URL` | redis://localhost:6379/0 | Redis connection URL |

See `.env.example` for all options.

---

## 📖 Documentation

- **[API Reference](omniscrape/docs/API_REFERENCE.md)** - Complete API documentation
- **[Setup Guide](omniscrape/docs/SETUP.md)** - Installation and configuration
- **[Evasion Strategies](omniscrape/docs/EVASION_STRATEGIES.md)** - Anti-detection techniques

Interactive docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific tests
pytest tests/unit/test_parsers.py -v
```

---

## 🔧 Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Format code
black .
isort .

# Lint
ruff check .

# Type check
mypy .
```

---

## 📊 Performance

| Metric | Target | Notes |
|--------|--------|-------|
| SERP Scrapes | 60+/min | With proxy rotation |
| Deep Scrapes | 30+/min | Content extraction included |
| Response Time | <1s | Cached/simple requests |
| Concurrency | 100+ | Async with uvloop |

---

## ⚠️ Disclaimer

This tool is provided for legitimate web scraping use cases such as:
- Academic research
- Price monitoring with permission
- Content aggregation with authorization
- SEO analysis

**Always respect:**
- Website Terms of Service
- robots.txt guidelines
- Rate limiting policies
- Local laws and regulations

Use responsibly.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ using FastAPI, Playwright, and Python**

</div>
