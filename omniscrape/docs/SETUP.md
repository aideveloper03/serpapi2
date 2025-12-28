# OmniScrape Engine - Setup Guide

## Quick Start

### Docker (Recommended)

The fastest way to get started is using Docker:

```bash
# Clone the repository
git clone https://github.com/your-org/omniscrape.git
cd omniscrape

# Copy environment file
cp .env.example .env

# Build and run
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

The API will be available at `http://localhost:8000`.

### Local Development

#### Prerequisites

- Python 3.11+
- Redis (optional, for caching)
- Tesseract OCR (optional, for CAPTCHA solving)

#### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy environment file
cp .env.example .env

# Run the application
python main.py
```

---

## Configuration

### Environment Variables

All configuration is done via environment variables or `.env` file:

#### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | OmniScrape Engine | Application name |
| `APP_VERSION` | 1.0.0 | Application version |
| `APP_ENV` | production | Environment (production/development) |
| `DEBUG` | false | Enable debug mode |
| `LOG_LEVEL` | INFO | Logging level |

#### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | 0.0.0.0 | Bind host |
| `PORT` | 8000 | Bind port |
| `WORKERS` | 4 | Number of workers |

#### Concurrency Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONCURRENT_SERP_SCRAPES` | 60 | Max concurrent search scrapes |
| `MAX_CONCURRENT_DEEP_SCRAPES` | 30 | Max concurrent deep scrapes |
| `REQUEST_TIMEOUT` | 30 | Request timeout in seconds |
| `CONNECT_TIMEOUT` | 10 | Connection timeout in seconds |

#### Redis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | redis://localhost:6379/0 | Redis connection URL |
| `REDIS_PASSWORD` | | Redis password |
| `CACHE_TTL` | 3600 | Cache TTL in seconds |
| `RATE_LIMIT_REQUESTS` | 100 | Rate limit requests per window |
| `RATE_LIMIT_WINDOW` | 60 | Rate limit window in seconds |

#### Proxy Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PROXY_LIST_URL` | (public list) | URL to fetch proxy list |
| `PROXY_VALIDATION_TIMEOUT` | 5 | Proxy validation timeout |
| `PROXY_POOL_SIZE` | 50 | Maximum proxy pool size |
| `CUSTOM_PROXY_URL` | | Custom proxy URL |
| `PROXY_ROTATION_INTERVAL` | 30 | Rotation interval in seconds |

#### Browser Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HEADLESS_MODE` | true | Run browser headless |
| `BROWSER_TIMEOUT` | 30000 | Browser timeout in ms |
| `MAX_BROWSER_INSTANCES` | 5 | Max browser instances |
| `STEALTH_MODE` | true | Enable stealth mode |

#### Crawler Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CRAWL_DEPTH` | 3 | Maximum crawl depth |
| `MAX_PAGES_PER_CRAWL` | 100 | Max pages per crawl |
| `CRAWL_DELAY_MIN` | 1.0 | Minimum delay between requests |
| `CRAWL_DELAY_MAX` | 3.0 | Maximum delay between requests |
| `RESPECT_ROBOTS_TXT` | false | Respect robots.txt |

---

## Docker Deployment

### Basic Deployment

```bash
docker-compose up -d
```

### Production Deployment

For production, consider:

1. **Use specific image tags**:
```yaml
services:
  omniscrape:
    image: omniscrape:1.0.0
```

2. **Configure resource limits**:
```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

3. **Enable persistent storage**:
```yaml
volumes:
  - ./logs:/app/logs
  - ./data:/app/data
```

4. **Configure health checks**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Scaling

For horizontal scaling:

```bash
docker-compose up -d --scale omniscrape=3
```

Use a load balancer (nginx, traefik) in front of the instances.

---

## Custom Proxy Configuration

### Using Custom Proxies

Set the `CUSTOM_PROXY_URL` environment variable:

```bash
# HTTP Proxy
CUSTOM_PROXY_URL=http://user:pass@proxy.example.com:8080

# SOCKS5 Proxy
CUSTOM_PROXY_URL=socks5://user:pass@proxy.example.com:1080
```

### Residential Proxy Services

For best results, use residential proxies:

1. **Bright Data**: Set `CUSTOM_PROXY_URL` to your Bright Data endpoint
2. **Oxylabs**: Use their residential proxy endpoint
3. **Smartproxy**: Configure their rotating residential proxies

Example configuration:
```bash
CUSTOM_PROXY_URL=http://username:password@residential.proxy.com:22225
```

---

## Kubernetes Deployment

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: omniscrape
spec:
  replicas: 3
  selector:
    matchLabels:
      app: omniscrape
  template:
    metadata:
      labels:
        app: omniscrape
    spec:
      containers:
      - name: omniscrape
        image: omniscrape:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: redis://redis:6379/0
        resources:
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: omniscrape
spec:
  selector:
    app: omniscrape
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## Troubleshooting

### Common Issues

#### "Connection refused" errors

- Check if Redis is running
- Verify `REDIS_URL` is correct
- Ensure ports are not blocked by firewall

#### Playwright browser issues

```bash
# Install system dependencies
playwright install-deps chromium

# Reinstall browsers
playwright install chromium
```

#### High memory usage

- Reduce `MAX_BROWSER_INSTANCES`
- Lower `PROXY_POOL_SIZE`
- Enable memory limits in Docker

#### Rate limiting triggered

- Increase `CRAWL_DELAY_MIN` and `CRAWL_DELAY_MAX`
- Use better proxies
- Enable `STEALTH_MODE`

### Logs

View logs:
```bash
# Docker
docker-compose logs -f omniscrape

# Local
tail -f logs/omniscrape.log
```

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/health/detailed

# Readiness
curl http://localhost:8000/ready
```

---

## Performance Tuning

### For High Volume

1. **Increase workers**: `WORKERS=8`
2. **Increase concurrency**: `MAX_CONCURRENT_SERP_SCRAPES=100`
3. **Use Redis cluster**: Multiple Redis instances
4. **Use premium proxies**: Residential proxy services

### For Stealth

1. **Enable all anti-detection**: `STEALTH_MODE=true`
2. **Increase delays**: `CRAWL_DELAY_MIN=2.0`, `CRAWL_DELAY_MAX=5.0`
3. **Use GhostNet mode**: Set `crawler_mode=ghostnet`
4. **Rotate fingerprints**: `ROTATE_FINGERPRINT=true`

---

## API Documentation

Access interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
