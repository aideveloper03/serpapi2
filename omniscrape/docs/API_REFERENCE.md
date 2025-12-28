# OmniScrape Engine - API Reference

## Overview

OmniScrape Engine provides a comprehensive REST API for web scraping and search engine data extraction. All endpoints return JSON responses with consistent structure.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API does not require authentication. Rate limiting is applied per IP address.

## Rate Limiting

- **Limit**: 100 requests per minute per IP
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Response**: HTTP 429 when exceeded

---

## Search API

### POST /api/v1/search

Execute a search query with automatic engine fallback.

**Request Body:**

```json
{
  "query": "string (required)",
  "engine": "auto|google|bing|duckduckgo|yahoo|yandex",
  "vertical": "all|news|images|videos",
  "num_results": 10,
  "page": 1,
  "country": "us",
  "language": "en",
  "time_range": "d|w|m|y",
  "safe_search": true,
  "use_proxy": true,
  "force_browser": false
}
```

**Response:**

```json
{
  "success": true,
  "query": "search query",
  "engine": "google",
  "vertical": "all",
  "total_results": 1000000,
  "results": [
    {
      "position": 1,
      "title": "Result Title",
      "url": "https://example.com",
      "description": "Result description snippet",
      "displayed_url": "example.com",
      "date": "2024-01-15",
      "thumbnail": null,
      "source": "google",
      "cached_url": null,
      "extra": null
    }
  ],
  "fallback_used": false,
  "fallback_chain": ["google"],
  "execution_time_ms": 1234.56,
  "trace_id": "abc12345",
  "cached": false
}
```

### GET /api/v1/search

Quick search via query parameters.

**Parameters:**
- `q` (required): Search query
- `engine`: Search engine (default: auto)
- `vertical`: Search vertical (default: all)
- `num`: Number of results (default: 10)
- `page`: Page number (default: 1)
- `country`: Country code
- `language`: Language code
- `time_range`: Time filter (d/w/m/y)
- `safe`: Safe search (default: true)

### Specialized Search Endpoints

- `POST /api/v1/search/google` - Google search specifically
- `POST /api/v1/search/bing` - Bing search specifically
- `POST /api/v1/search/duckduckgo` - DuckDuckGo search specifically
- `POST /api/v1/search/news` - News search across engines
- `POST /api/v1/search/images` - Image search
- `POST /api/v1/search/videos` - Video search

---

## Crawl API

### POST /api/v1/crawl

Crawl a website with content extraction.

**Request Body:**

```json
{
  "url": "https://example.com (required)",
  "depth": 1,
  "max_pages": 10,
  "crawler_mode": "simple|deep|stealth|ghostnet",
  "follow_external": false,
  "extract_content": true,
  "extract_contacts": true,
  "extract_metadata": true,
  "extract_schema": true,
  "respect_robots": false,
  "use_proxy": true,
  "custom_headers": {},
  "cookies": {},
  "wait_for_js": false,
  "js_wait_time": 2000
}
```

**Response:**

```json
{
  "success": true,
  "url": "https://example.com",
  "pages_crawled": 5,
  "depth_reached": 2,
  "pages": [
    {
      "url": "https://example.com",
      "status_code": 200,
      "final_url": null,
      "content": {
        "title": "Page Title",
        "text": "Extracted content...",
        "summary": "Auto-generated summary...",
        "authors": ["Author Name"],
        "publish_date": "2024-01-15",
        "content_type": "article",
        "word_count": 1500,
        "reading_time_minutes": 8,
        "language": "en",
        "keywords": ["keyword1", "keyword2"]
      },
      "contacts": {
        "emails": ["contact@example.com"],
        "phones": ["+1-555-123-4567"],
        "social_links": {
          "twitter": ["https://twitter.com/example"],
          "linkedin": ["https://linkedin.com/company/example"]
        },
        "addresses": ["123 Main St, City, ST 12345"]
      },
      "metadata": {
        "title": "Page Title",
        "description": "Meta description",
        "keywords": ["meta", "keywords"],
        "canonical_url": "https://example.com/page",
        "og_data": {
          "title": "OG Title",
          "description": "OG Description",
          "image": "https://example.com/image.jpg"
        },
        "twitter_data": {
          "card": "summary_large_image"
        },
        "structured_data": [],
        "favicon": "https://example.com/favicon.ico",
        "language": "en",
        "charset": "utf-8"
      },
      "links": ["https://example.com/page1", "..."],
      "internal_links": ["..."],
      "external_links": ["..."],
      "raw_html": null,
      "screenshot": null,
      "crawled_at": "2024-01-15T10:30:00Z"
    }
  ],
  "execution_time_ms": 5678.90,
  "trace_id": "def67890",
  "errors": []
}
```

### Crawler Modes

| Mode | Description |
|------|-------------|
| `simple` | Single page extraction using HTTP client |
| `deep` | Follow links up to specified depth |
| `stealth` | Use headless browser with anti-detection |
| `ghostnet` | Use GhostNet Protocol for maximum stealth |

### Specialized Crawl Endpoints

- `POST /api/v1/crawl/stealth` - Stealth browser crawl
- `POST /api/v1/crawl/ghostnet` - GhostNet Protocol crawl
- `POST /api/v1/crawl/deep` - Deep crawl with link following
- `POST /api/v1/crawl/single` - Single page crawl

---

## Data Mining API

### POST /api/v1/mine

Extract structured data from multiple URLs.

**Request Body:**

```json
{
  "urls": ["https://example1.com", "https://example2.com"],
  "extract_emails": true,
  "extract_phones": true,
  "extract_social": true,
  "extract_addresses": true,
  "extract_company_info": true,
  "parallel": true
}
```

**Response:**

```json
{
  "success": true,
  "urls_processed": 2,
  "results": [
    {
      "url": "https://example1.com",
      "emails": ["contact@example1.com"],
      "phones": ["+1-555-111-1111"],
      "social_links": {
        "twitter": ["https://twitter.com/example1"]
      },
      "addresses": ["123 First St"],
      "company_info": {
        "name": "Example Corp",
        "description": "Company description"
      }
    }
  ],
  "execution_time_ms": 3456.78,
  "trace_id": "ghi12345",
  "errors": []
}
```

### Specialized Mining Endpoints

- `GET /api/v1/mine/emails?urls=url1&urls=url2` - Extract emails only
- `GET /api/v1/mine/contacts?urls=url1&urls=url2` - Extract all contacts
- `POST /api/v1/mine/batch` - Batch processing for large URL lists

---

## Health Endpoints

### GET /health

Basic health check.

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "redis_connected": true,
  "proxy_pool_size": 45,
  "active_requests": 3
}
```

### GET /health/detailed

Detailed health information with component status.

### GET /ready

Kubernetes readiness probe.

### GET /live

Kubernetes liveness probe.

---

## Error Responses

All errors follow a consistent format:

```json
{
  "success": false,
  "error": "Error description",
  "error_code": "ERROR_CODE",
  "trace_id": "abc12345",
  "details": null
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `SEARCH_ERROR` | 500 | Search operation failed |
| `CRAWL_ERROR` | 500 | Crawl operation failed |
| `MINE_ERROR` | 500 | Data mining failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## Response Headers

All responses include:

- `X-Trace-ID`: Unique request trace ID
- `X-Request-ID`: Unique request identifier
- `X-Response-Time`: Response time in milliseconds
- `X-RateLimit-Limit`: Rate limit ceiling
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

---

## Examples

### cURL: Basic Search

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "python web scraping", "num_results": 5}'
```

### cURL: Quick Search

```bash
curl "http://localhost:8000/api/v1/search?q=python%20tutorial&num=10"
```

### cURL: Stealth Crawl

```bash
curl -X POST "http://localhost:8000/api/v1/crawl/stealth" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "depth": 2}'
```

### Python: Search with httpx

```python
import httpx

async def search():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/search",
            json={
                "query": "machine learning",
                "engine": "auto",
                "num_results": 20
            }
        )
        data = response.json()
        for result in data["results"]:
            print(f"{result['position']}. {result['title']}")
            print(f"   {result['url']}")
```

### Python: Data Mining

```python
import httpx

async def mine_contacts():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/mine",
            json={
                "urls": [
                    "https://company1.com/contact",
                    "https://company2.com/about"
                ],
                "extract_emails": True,
                "extract_phones": True,
                "parallel": True
            }
        )
        data = response.json()
        for result in data["results"]:
            print(f"URL: {result['url']}")
            print(f"Emails: {result['emails']}")
            print(f"Phones: {result['phones']}")
```
