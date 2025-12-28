"""
OmniScrape Engine - Stealth Browser
Playwright-based browser with comprehensive anti-detection measures
"""

import asyncio
import random
import json
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager

from config import settings
from utils import get_logger
from services.captcha_handler import captcha_handler

logger = get_logger(__name__)


class StealthBrowser:
    """
    Playwright-based browser with advanced stealth features:
    - WebDriver detection bypass
    - Canvas/WebGL fingerprint spoofing
    - AudioContext fingerprint spoofing
    - Navigator property overrides
    - Timezone and language spoofing
    - Human-like behavior simulation
    """
    
    # Stealth JavaScript to inject
    STEALTH_JS = '''
    // Overwrite the navigator.webdriver property
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });
    
    // Remove automation-related properties
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    
    // Override chrome.runtime
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
    
    // Override permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    
    // Override plugins to look like a real browser
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const plugins = [
                {
                    0: {type: "application/pdf", suffixes: "pdf"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                },
                {
                    0: {type: "application/pdf", suffixes: "pdf"},
                    description: "Portable Document Format",
                    filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                    length: 1,
                    name: "Chrome PDF Viewer"
                },
                {
                    0: {type: "application/x-nacl", suffixes: ""},
                    1: {type: "application/x-pnacl", suffixes: ""},
                    description: "Native Client Executable",
                    filename: "internal-nacl-plugin",
                    length: 2,
                    name: "Native Client"
                }
            ];
            plugins.item = (i) => plugins[i];
            plugins.namedItem = (name) => plugins.find(p => p.name === name);
            plugins.refresh = () => {};
            return plugins;
        },
        configurable: true
    });
    
    // Override languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
        configurable: true
    });
    
    // Override platform
    Object.defineProperty(navigator, 'platform', {
        get: () => 'Win32',
        configurable: true
    });
    
    // Override hardware concurrency
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8,
        configurable: true
    });
    
    // Override device memory
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8,
        configurable: true
    });
    
    // Mock WebGL
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';
        }
        return getParameter.call(this, parameter);
    };
    
    // Mock canvas fingerprint
    const toDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        if (type === 'image/png' && this.width === 220 && this.height === 30) {
            // Add noise to canvas fingerprint
            const context = this.getContext('2d');
            const imageData = context.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imageData.data.length; i += 4) {
                imageData.data[i] += Math.floor(Math.random() * 3);
            }
            context.putImageData(imageData, 0, 0);
        }
        return toDataURL.apply(this, arguments);
    };
    
    // Mock AudioContext fingerprint
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
        const originalCreateOscillator = AudioContext.prototype.createOscillator;
        AudioContext.prototype.createOscillator = function() {
            const oscillator = originalCreateOscillator.apply(this, arguments);
            oscillator._isModified = true;
            return oscillator;
        };
    }
    
    // Override Date to match timezone
    const originalDate = Date;
    class ModifiedDate extends originalDate {
        constructor(...args) {
            super(...args);
        }
        getTimezoneOffset() {
            return -300; // EST
        }
    }
    
    // Override connection info
    Object.defineProperty(navigator, 'connection', {
        get: () => ({
            effectiveType: '4g',
            rtt: 50,
            downlink: 10,
            saveData: false
        }),
        configurable: true
    });
    
    // Override battery
    if (navigator.getBattery) {
        navigator.getBattery = () => Promise.resolve({
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: 1.0
        });
    }
    
    console.log('Stealth mode activated');
    '''
    
    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None
    
    async def __aenter__(self):
        await self.launch()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def launch(self) -> None:
        """Launch the stealth browser"""
        from playwright.async_api import async_playwright
        
        self._playwright = await async_playwright().start()
        
        # Launch with specific arguments to avoid detection
        self._browser = await self._playwright.chromium.launch(
            headless=settings.headless_mode,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-infobars',
                '--disable-background-networking',
                '--disable-default-apps',
                '--disable-extensions',
                '--disable-gpu',
                '--disable-sync',
                '--no-first-run',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--window-size=1920,1080',
                '--start-maximized',
            ],
        )
        
        # Create context with realistic settings
        self._context = await self._browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=self._get_random_user_agent(),
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            permissions=['geolocation'],
            color_scheme='light',
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            java_script_enabled=True,
            ignore_https_errors=True,
        )
        
        # Add stealth scripts to be executed on every page
        await self._context.add_init_script(self.STEALTH_JS)
        
        # Create the main page
        self._page = await self._context.new_page()
        
        # Set extra HTTP headers
        await self._page.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
        
        logger.info("stealth_browser_launched")
    
    async def close(self) -> None:
        """Close the browser"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        
        logger.info("stealth_browser_closed")
    
    def _get_random_user_agent(self) -> str:
        """Get a random realistic user agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        ]
        return random.choice(user_agents)
    
    async def fetch_page(self, url: str, timeout: int = 30000) -> str:
        """Fetch a page with stealth measures"""
        if not self._page:
            await self.launch()
        
        try:
            # Simulate human-like behavior before navigation
            await self._pre_navigation_behavior()
            
            # Navigate to the page
            response = await self._page.goto(
                url,
                wait_until='networkidle',
                timeout=timeout,
            )
            
            # Wait a bit after load
            await asyncio.sleep(random.uniform(1, 2))
            
            # Simulate post-navigation behavior
            await self._post_navigation_behavior()
            
            # Get page content
            content = await self._page.content()
            
            # Check for CAPTCHA
            has_captcha, solution = await captcha_handler.handle_page(
                content,
                page=self._page,
            )
            
            if has_captcha and solution and solution.success:
                # Re-fetch content after CAPTCHA solve
                await asyncio.sleep(2)
                content = await self._page.content()
            
            return content
            
        except Exception as e:
            logger.error("stealth_fetch_error", url=url, error=str(e))
            raise
    
    async def fetch_page_with_url(self, url: str, timeout: int = 30000) -> Tuple[str, str]:
        """Fetch a page and return content with final URL"""
        content = await self.fetch_page(url, timeout)
        final_url = self._page.url
        return content, final_url
    
    async def _pre_navigation_behavior(self) -> None:
        """Simulate human behavior before navigation"""
        # Random mouse movement
        for _ in range(random.randint(1, 3)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            await self._page.mouse.move(x, y, steps=random.randint(5, 15))
            await asyncio.sleep(random.uniform(0.05, 0.2))
    
    async def _post_navigation_behavior(self) -> None:
        """Simulate human behavior after page load"""
        # Random scrolling
        scroll_amount = random.randint(100, 400)
        await self._page.evaluate(f'window.scrollBy(0, {scroll_amount})')
        await asyncio.sleep(random.uniform(0.3, 0.8))
        
        # More mouse movement
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 1200)
            y = random.randint(100, 800)
            await self._page.mouse.move(x, y, steps=random.randint(10, 25))
            await asyncio.sleep(random.uniform(0.1, 0.3))
    
    async def click(self, selector: str) -> None:
        """Click an element with human-like behavior"""
        element = await self._page.query_selector(selector)
        if element:
            box = await element.bounding_box()
            if box:
                # Move mouse naturally to element
                x = box['x'] + random.uniform(box['width'] * 0.2, box['width'] * 0.8)
                y = box['y'] + random.uniform(box['height'] * 0.2, box['height'] * 0.8)
                
                await self._page.mouse.move(x, y, steps=random.randint(15, 30))
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                await self._page.mouse.down()
                await asyncio.sleep(random.uniform(0.05, 0.15))
                await self._page.mouse.up()
    
    async def type_text(self, selector: str, text: str) -> None:
        """Type text with human-like delays"""
        await self.click(selector)
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        for char in text:
            await self._page.keyboard.type(char)
            # Random delay between keystrokes
            await asyncio.sleep(random.uniform(0.05, 0.2))
    
    async def scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the page like a human"""
        total_height = await self._page.evaluate('document.body.scrollHeight')
        current_position = 0
        
        while current_position < total_height:
            scroll_amount = random.randint(200, 500)
            current_position += scroll_amount
            
            await self._page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
            # Update total height in case of infinite scroll
            total_height = await self._page.evaluate('document.body.scrollHeight')
    
    async def take_screenshot(self, path: str) -> None:
        """Take a screenshot"""
        await self._page.screenshot(path=path, full_page=True)
    
    async def get_cookies(self) -> List[Dict]:
        """Get all cookies"""
        return await self._context.cookies()
    
    async def set_cookies(self, cookies: List[Dict]) -> None:
        """Set cookies"""
        await self._context.add_cookies(cookies)
    
    async def execute_js(self, script: str) -> Any:
        """Execute JavaScript on the page"""
        return await self._page.evaluate(script)
    
    @property
    def page(self):
        """Get the Playwright page object"""
        return self._page
