# OmniScrape Engine - Evasion Strategies

This document details the anti-detection and evasion techniques implemented in OmniScrape Engine. These strategies work together to make scraping activities indistinguishable from legitimate browser traffic.

---

## 1. Browser Fingerprint Spoofing

### User-Agent Rotation

OmniScrape maintains a pool of realistic User-Agent strings representing actual browser versions:

```python
# Example User-Agents in rotation
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
```

### Sec-Ch-Ua Headers

Modern browsers send Client Hints. OmniScrape sends matching hints:

```http
Sec-Ch-Ua: "Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"
Sec-Ch-Ua-Mobile: ?0
Sec-Ch-Ua-Platform: "Windows"
```

### Complete Header Profiles

Each browser profile includes all expected headers:
- Accept
- Accept-Language
- Accept-Encoding
- Sec-Fetch-* headers
- Connection and caching headers

---

## 2. TLS Fingerprint Mimicking

### The Problem

Every TLS client has a unique fingerprint based on:
- Supported cipher suites
- TLS extensions
- Curve preferences
- Signature algorithms

Bot detection services fingerprint TLS connections to identify automated traffic.

### Our Solution

OmniScrape uses `curl-cffi` to impersonate real browser TLS fingerprints:

```python
from curl_cffi.requests import AsyncSession

async with AsyncSession(impersonate="chrome120") as session:
    response = await session.get(url)
```

Supported browser impersonations:
- Chrome 118, 119, 120
- Firefox 120, 121
- Safari 17
- Edge 120

---

## 3. IP Management & Proxy Rotation

### Proxy Pool Management

OmniScrape maintains a validated proxy pool:

1. **Automatic fetching** from public proxy lists
2. **Validation** before adding to pool
3. **Health monitoring** with success rate tracking
4. **Intelligent rotation** based on performance

### IP Spoofing Headers

In addition to proxies, IP spoofing headers are added:

```http
X-Forwarded-For: 203.0.113.42
X-Real-IP: 203.0.113.42
Via: 1.1 203.0.113.42
Forwarded: for=203.0.113.42
X-Originating-IP: 203.0.113.42
X-Client-IP: 203.0.113.42
```

### Per-Domain Blocking Detection

The proxy manager tracks which proxies are blocked on specific domains and avoids using them.

---

## 4. Canvas & WebGL Fingerprint Spoofing

### The Problem

Websites can fingerprint browsers by:
- Reading canvas rendering output
- Querying WebGL renderer info
- Analyzing font rendering

### Our Solution

In Playwright stealth mode, we inject JavaScript to spoof these:

```javascript
// Canvas fingerprint noise
const toDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    const context = this.getContext('2d');
    const imageData = context.getImageData(0, 0, this.width, this.height);
    for (let i = 0; i < imageData.data.length; i += 4) {
        imageData.data[i] += Math.floor(Math.random() * 3);
    }
    context.putImageData(imageData, 0, 0);
    return toDataURL.apply(this, arguments);
};

// WebGL vendor/renderer spoofing
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.call(this, parameter);
};
```

---

## 5. AudioContext Fingerprint Spoofing

### The Technique

Websites can generate unique fingerprints from AudioContext oscillator output.

### Our Defense

We modify the AudioContext to add subtle variations:

```javascript
const AudioContext = window.AudioContext || window.webkitAudioContext;
if (AudioContext) {
    const originalCreateOscillator = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function() {
        const oscillator = originalCreateOscillator.apply(this, arguments);
        oscillator._isModified = true;
        return oscillator;
    };
}
```

---

## 6. Navigator Property Overrides

We override navigator properties to match real browsers:

```javascript
// Hide automation
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// Set realistic plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        {name: "Chrome PDF Plugin"},
        {name: "Chrome PDF Viewer"},
        {name: "Native Client"}
    ]
});

// Hardware info
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8
});

Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8
});
```

---

## 7. Cookie Management & Session Persistence

### Realistic Cookies

OmniScrape generates and maintains realistic session cookies:

```python
# Example cookies for Google
{
    "CONSENT": "YES+cb.20231005-17-p0.en+FX+123",
    "SOCS": "CAESHAgBEhJnd3NfMjAyMzEwMDUtMF9SQzEaAmVuIAEaBgiA_9CqBg",
    "NID": "511=...",
}
```

### Session Consistency

GhostNet Protocol maintains sessions across requests to the same domain.

---

## 8. Human Behavior Simulation

### Mouse Movements

Before clicks, we simulate natural mouse movement:

```python
async def _human_like_click(self, page, box):
    # Random point within element
    x = box['x'] + random.uniform(box['width'] * 0.2, box['width'] * 0.8)
    y = box['y'] + random.uniform(box['height'] * 0.2, box['height'] * 0.8)
    
    # Move with natural curve
    await page.mouse.move(x, y, steps=random.randint(20, 40))
    
    # Natural click timing
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.05, 0.15))
    await page.mouse.up()
```

### Scrolling Behavior

We simulate natural scrolling patterns:

```python
async def _post_navigation_behavior(self):
    scroll_amount = random.randint(100, 400)
    await self._page.evaluate(f'window.scrollBy(0, {scroll_amount})')
    await asyncio.sleep(random.uniform(0.3, 0.8))
```

### Typing Simulation

When entering text, we add human-like delays:

```python
async def type_text(self, selector, text):
    for char in text:
        await self._page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.2))
```

---

## 9. GhostNet Protocol

Our innovative GhostNet Protocol combines multiple advanced techniques:

### Neural Timing Engine

Uses attention curve modeling for realistic request timing:

```python
ATTENTION_CURVE = [
    (0.0, 0.5),   # Initial interest
    (0.2, 0.8),   # Engagement increase
    (0.5, 1.0),   # Peak attention
    (0.7, 0.7),   # Attention decay
    (0.9, 0.4),   # Fatigue
    (1.0, 0.2),   # End of session
]
```

### Spectral Header Generation

Dynamically generates headers matching target site expectations.

### Echo Navigation

Simulates realistic browsing journeys:
- Search engine → target site
- Social media → target site
- Site exploration patterns

### Quantum Request Distribution

Unpredictable request timing using multiple random distributions:

```python
def get_quantum_delay(self):
    value = (
        random.gauss(0.5, 0.2) +
        random.betavariate(2, 5) +
        random.triangular(0, 1, 0.3)
    ) / 3
    delay = math.exp(value * 3) - 1
    delay += random.paretovariate(3) * 0.1
    return delay
```

---

## 10. CAPTCHA Avoidance & Solving

### Avoidance Strategies

1. **TLS fingerprinting** to avoid triggering CAPTCHAs
2. **Behavioral mimicking** to pass bot scores
3. **Session persistence** to maintain trusted state
4. **Slow, varied request timing**

### Solving Strategies

When CAPTCHAs are unavoidable:

1. **Cloudflare**: Browser automation with behavior simulation
2. **reCAPTCHA v2**: Checkbox clicking with human-like interaction
3. **reCAPTCHA v3**: High-score through stealth browsing
4. **Image CAPTCHAs**: OCR with Tesseract

---

## 11. Request Timing & Rate Control

### Adaptive Delays

Delays are calculated based on:
- Content length (reading time)
- Session position (attention curve)
- Time of day (circadian rhythm)

### Burst Avoidance

Requests are distributed to avoid pattern detection:
- Random intervals between requests
- Session-based pacing
- Per-domain rate limiting

---

## 12. Cascading Fallback

When detection occurs, OmniScrape automatically:

1. **Detects** block/CAPTCHA
2. **Switches** to next engine/method
3. **Escalates** to browser mode
4. **Uses** alternative parsers (regex fallback)

Fallback chain:
```
Google → DuckDuckGo → Bing → Yahoo → Yandex → Browser Mode → Regex Fallback
```

---

## Best Practices

### For Maximum Stealth

1. **Use GhostNet mode** for sensitive targets
2. **Enable all spoofing** options
3. **Use residential proxies**
4. **Increase delays** between requests
5. **Maintain sessions** across requests

### For Speed vs. Stealth Balance

1. **Use AUTO engine** for search
2. **Use SIMPLE mode** for basic crawls
3. **Enable proxy rotation**
4. **Keep default delays**

### Monitoring & Tuning

1. **Check success rates** in proxy stats
2. **Monitor for CAPTCHA** occurrences
3. **Adjust timing** based on target site
4. **Rotate fingerprints** periodically

---

## Disclaimer

These techniques are provided for legitimate web scraping use cases such as:
- Academic research
- Price monitoring
- Content aggregation with permission
- SEO analysis

Always respect website terms of service and robots.txt (when appropriate). Use responsibly.
