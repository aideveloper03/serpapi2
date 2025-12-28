"""
OmniScrape Engine - CAPTCHA Handler
Custom CAPTCHA detection and solving without external paid APIs
"""

import asyncio
import base64
import io
import re
import random
import time
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from bs4 import BeautifulSoup

from config import settings
from utils import get_logger

logger = get_logger(__name__)


class CaptchaType(Enum):
    """Types of CAPTCHA challenges"""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    CLOUDFLARE = "cloudflare"
    IMAGE_CAPTCHA = "image_captcha"
    TEXT_CAPTCHA = "text_captcha"
    SLIDER_CAPTCHA = "slider"
    FUNCAPTCHA = "funcaptcha"
    UNKNOWN = "unknown"


@dataclass
class CaptchaChallenge:
    """Detected CAPTCHA challenge"""
    captcha_type: CaptchaType
    site_key: Optional[str] = None
    action: Optional[str] = None
    data_s: Optional[str] = None
    image_url: Optional[str] = None
    image_data: Optional[bytes] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class CaptchaSolution:
    """Solution to a CAPTCHA challenge"""
    success: bool
    token: Optional[str] = None
    answer: Optional[str] = None
    error: Optional[str] = None


class CaptchaDetector:
    """Detects CAPTCHA presence and type in web pages"""
    
    # Detection patterns
    RECAPTCHA_PATTERNS = [
        r'class="g-recaptcha"',
        r'data-sitekey="([^"]+)"',
        r'grecaptcha\.execute',
        r'www\.google\.com/recaptcha',
        r'recaptcha/api',
    ]
    
    HCAPTCHA_PATTERNS = [
        r'class="h-captcha"',
        r'data-hcaptcha-site-key',
        r'hcaptcha\.com',
        r'data-sitekey="([^"]+)".*h-captcha',
    ]
    
    CLOUDFLARE_PATTERNS = [
        r'cf-browser-verification',
        r'cf_chl_opt',
        r'cloudflare',
        r'__cf_bm',
        r'cf-ray',
        r'challenge-platform',
        r'turnstile',
    ]
    
    def detect(self, html: str, headers: Optional[Dict[str, str]] = None) -> Optional[CaptchaChallenge]:
        """Detect CAPTCHA type and extract relevant data"""
        html_lower = html.lower()
        
        # Check for Cloudflare first (most common)
        if self._is_cloudflare(html, headers):
            return CaptchaChallenge(
                captcha_type=CaptchaType.CLOUDFLARE,
                additional_data=self._extract_cloudflare_data(html),
            )
        
        # Check for reCAPTCHA
        recaptcha_data = self._detect_recaptcha(html)
        if recaptcha_data:
            return recaptcha_data
        
        # Check for hCaptcha
        hcaptcha_data = self._detect_hcaptcha(html)
        if hcaptcha_data:
            return hcaptcha_data
        
        # Check for image CAPTCHA
        image_captcha = self._detect_image_captcha(html)
        if image_captcha:
            return image_captcha
        
        # Generic CAPTCHA detection
        if any(word in html_lower for word in ['captcha', 'robot', 'human verification']):
            return CaptchaChallenge(captcha_type=CaptchaType.UNKNOWN)
        
        return None
    
    def _is_cloudflare(self, html: str, headers: Optional[Dict[str, str]] = None) -> bool:
        """Check if page is Cloudflare protected"""
        # Check headers
        if headers:
            if 'cf-ray' in headers or 'cf-cache-status' in headers:
                if 'challenge' in html.lower() or 'cf_chl' in html:
                    return True
        
        # Check HTML
        for pattern in self.CLOUDFLARE_PATTERNS:
            if re.search(pattern, html, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_recaptcha(self, html: str) -> Optional[CaptchaChallenge]:
        """Detect and extract reCAPTCHA data"""
        # Check for reCAPTCHA v2
        if 'g-recaptcha' in html or 'grecaptcha' in html.lower():
            # Extract site key
            site_key_match = re.search(r'data-sitekey="([^"]+)"', html)
            site_key = site_key_match.group(1) if site_key_match else None
            
            # Determine v2 or v3
            is_v3 = 'grecaptcha.execute' in html and 'action' in html
            
            if is_v3:
                # Extract action
                action_match = re.search(r'action["\']?\s*:\s*["\']([^"\']+)["\']', html)
                action = action_match.group(1) if action_match else None
                
                return CaptchaChallenge(
                    captcha_type=CaptchaType.RECAPTCHA_V3,
                    site_key=site_key,
                    action=action,
                )
            else:
                # Extract data-s for invisible reCAPTCHA
                data_s_match = re.search(r'data-s="([^"]+)"', html)
                data_s = data_s_match.group(1) if data_s_match else None
                
                return CaptchaChallenge(
                    captcha_type=CaptchaType.RECAPTCHA_V2,
                    site_key=site_key,
                    data_s=data_s,
                )
        
        return None
    
    def _detect_hcaptcha(self, html: str) -> Optional[CaptchaChallenge]:
        """Detect and extract hCaptcha data"""
        if 'h-captcha' in html or 'hcaptcha' in html.lower():
            site_key_match = re.search(r'data-sitekey="([^"]+)"', html)
            site_key = site_key_match.group(1) if site_key_match else None
            
            return CaptchaChallenge(
                captcha_type=CaptchaType.HCAPTCHA,
                site_key=site_key,
            )
        
        return None
    
    def _detect_image_captcha(self, html: str) -> Optional[CaptchaChallenge]:
        """Detect image-based CAPTCHA"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for CAPTCHA images
        captcha_imgs = soup.find_all('img', src=re.compile(r'captcha', re.I))
        
        if captcha_imgs:
            img = captcha_imgs[0]
            return CaptchaChallenge(
                captcha_type=CaptchaType.IMAGE_CAPTCHA,
                image_url=img.get('src'),
            )
        
        return None
    
    def _extract_cloudflare_data(self, html: str) -> Dict[str, Any]:
        """Extract Cloudflare challenge data"""
        data = {}
        
        # Extract ray ID
        ray_match = re.search(r'cf-ray["\']?\s*:\s*["\']?([a-f0-9-]+)', html, re.I)
        if ray_match:
            data['ray_id'] = ray_match.group(1)
        
        # Extract challenge options
        opts_match = re.search(r'cf_chl_opt\s*=\s*(\{[^}]+\})', html)
        if opts_match:
            data['chl_opts'] = opts_match.group(1)
        
        return data


class CaptchaSolver:
    """
    Attempts to solve CAPTCHA challenges using local methods.
    Focuses on browser automation and behavioral mimicking.
    """
    
    def __init__(self):
        self._ocr_available = False
        try:
            import pytesseract
            from PIL import Image
            self._ocr_available = True
        except ImportError:
            logger.warning("OCR not available - pytesseract or PIL not installed")
    
    async def solve(
        self,
        challenge: CaptchaChallenge,
        page=None,  # Playwright page object
    ) -> CaptchaSolution:
        """Attempt to solve a CAPTCHA challenge"""
        
        if challenge.captcha_type == CaptchaType.CLOUDFLARE:
            return await self._solve_cloudflare(challenge, page)
        
        elif challenge.captcha_type == CaptchaType.RECAPTCHA_V2:
            return await self._solve_recaptcha_v2(challenge, page)
        
        elif challenge.captcha_type == CaptchaType.RECAPTCHA_V3:
            return await self._solve_recaptcha_v3(challenge, page)
        
        elif challenge.captcha_type == CaptchaType.IMAGE_CAPTCHA:
            return await self._solve_image_captcha(challenge)
        
        elif challenge.captcha_type == CaptchaType.HCAPTCHA:
            return await self._solve_hcaptcha(challenge, page)
        
        return CaptchaSolution(
            success=False,
            error=f"Unsupported CAPTCHA type: {challenge.captcha_type.value}",
        )
    
    async def _solve_cloudflare(
        self,
        challenge: CaptchaChallenge,
        page,
    ) -> CaptchaSolution:
        """
        Solve Cloudflare challenge using browser automation.
        Uses behavioral mimicking to pass the challenge.
        """
        if not page:
            return CaptchaSolution(
                success=False,
                error="Browser page required for Cloudflare bypass",
            )
        
        try:
            # Wait for the challenge
            await asyncio.sleep(random.uniform(2, 4))
            
            # Simulate human-like behavior
            await self._simulate_human_behavior(page)
            
            # Look for the checkbox
            checkbox_selectors = [
                'input[type="checkbox"]',
                '.cf-turnstile',
                '#cf-spinner',
                '[data-callback]',
            ]
            
            for selector in checkbox_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        # Move mouse naturally to element
                        box = await element.bounding_box()
                        if box:
                            await self._human_like_click(page, box)
                            await asyncio.sleep(random.uniform(3, 6))
                            break
                except:
                    continue
            
            # Wait for redirect/resolution
            await asyncio.sleep(random.uniform(3, 5))
            
            # Check if challenge was solved
            content = await page.content()
            if 'cf-browser-verification' not in content.lower():
                return CaptchaSolution(success=True)
            
            return CaptchaSolution(
                success=False,
                error="Cloudflare challenge not resolved",
            )
            
        except Exception as e:
            return CaptchaSolution(
                success=False,
                error=f"Cloudflare solve error: {str(e)}",
            )
    
    async def _solve_recaptcha_v2(
        self,
        challenge: CaptchaChallenge,
        page,
    ) -> CaptchaSolution:
        """
        Attempt to solve reCAPTCHA v2 by clicking the checkbox.
        For image challenges, this will likely fail without external API.
        """
        if not page:
            return CaptchaSolution(
                success=False,
                error="Browser page required for reCAPTCHA",
            )
        
        try:
            # Simulate human behavior before interaction
            await self._simulate_human_behavior(page)
            
            # Find and click the reCAPTCHA checkbox
            recaptcha_frame = await page.query_selector('iframe[src*="recaptcha"]')
            
            if recaptcha_frame:
                frame = await recaptcha_frame.content_frame()
                if frame:
                    checkbox = await frame.query_selector('.recaptcha-checkbox-border')
                    if checkbox:
                        box = await checkbox.bounding_box()
                        if box:
                            await self._human_like_click(page, box)
                            await asyncio.sleep(random.uniform(2, 4))
                            
                            # Check if solved (green checkmark)
                            is_checked = await frame.query_selector('.recaptcha-checkbox-checked')
                            if is_checked:
                                # Get the token
                                token = await page.evaluate(
                                    'document.getElementById("g-recaptcha-response")?.value'
                                )
                                return CaptchaSolution(success=True, token=token)
            
            return CaptchaSolution(
                success=False,
                error="reCAPTCHA v2 requires image solving",
            )
            
        except Exception as e:
            return CaptchaSolution(
                success=False,
                error=f"reCAPTCHA v2 solve error: {str(e)}",
            )
    
    async def _solve_recaptcha_v3(
        self,
        challenge: CaptchaChallenge,
        page,
    ) -> CaptchaSolution:
        """
        reCAPTCHA v3 is score-based.
        We rely on stealth browsing to get a high score.
        """
        if not page:
            return CaptchaSolution(
                success=False,
                error="Browser page required for reCAPTCHA v3",
            )
        
        try:
            # v3 executes automatically - wait and check for token
            await asyncio.sleep(random.uniform(2, 3))
            
            # Try to get the token
            token = await page.evaluate('''
                () => {
                    return new Promise((resolve) => {
                        if (typeof grecaptcha !== 'undefined') {
                            grecaptcha.ready(async () => {
                                try {
                                    const token = await grecaptcha.execute();
                                    resolve(token);
                                } catch (e) {
                                    resolve(null);
                                }
                            });
                        } else {
                            resolve(null);
                        }
                    });
                }
            ''')
            
            if token:
                return CaptchaSolution(success=True, token=token)
            
            return CaptchaSolution(
                success=False,
                error="Failed to get reCAPTCHA v3 token",
            )
            
        except Exception as e:
            return CaptchaSolution(
                success=False,
                error=f"reCAPTCHA v3 solve error: {str(e)}",
            )
    
    async def _solve_hcaptcha(
        self,
        challenge: CaptchaChallenge,
        page,
    ) -> CaptchaSolution:
        """
        Attempt to solve hCaptcha checkbox.
        Image challenges require external APIs.
        """
        if not page:
            return CaptchaSolution(
                success=False,
                error="Browser page required for hCaptcha",
            )
        
        try:
            await self._simulate_human_behavior(page)
            
            # Find hCaptcha frame
            hcaptcha_frame = await page.query_selector('iframe[src*="hcaptcha"]')
            
            if hcaptcha_frame:
                frame = await hcaptcha_frame.content_frame()
                if frame:
                    checkbox = await frame.query_selector('#checkbox')
                    if checkbox:
                        box = await checkbox.bounding_box()
                        if box:
                            await self._human_like_click(page, box)
                            await asyncio.sleep(random.uniform(2, 4))
            
            return CaptchaSolution(
                success=False,
                error="hCaptcha likely requires image solving",
            )
            
        except Exception as e:
            return CaptchaSolution(
                success=False,
                error=f"hCaptcha solve error: {str(e)}",
            )
    
    async def _solve_image_captcha(
        self,
        challenge: CaptchaChallenge,
    ) -> CaptchaSolution:
        """Solve simple image CAPTCHA using OCR"""
        if not self._ocr_available:
            return CaptchaSolution(
                success=False,
                error="OCR not available",
            )
        
        if not challenge.image_data and not challenge.image_url:
            return CaptchaSolution(
                success=False,
                error="No image data provided",
            )
        
        try:
            import pytesseract
            from PIL import Image
            
            # Get image data
            if challenge.image_data:
                image_bytes = challenge.image_data
            else:
                # Fetch image
                from services import network_client
                _, image_bytes, _ = await network_client.get(challenge.image_url)
                image_bytes = image_bytes.encode() if isinstance(image_bytes, str) else image_bytes
            
            # Load image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Preprocess image for better OCR
            image = self._preprocess_captcha_image(image)
            
            # Run OCR
            text = pytesseract.image_to_string(
                image,
                config='--psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            )
            
            text = text.strip()
            
            if text:
                return CaptchaSolution(success=True, answer=text)
            
            return CaptchaSolution(
                success=False,
                error="OCR failed to extract text",
            )
            
        except Exception as e:
            return CaptchaSolution(
                success=False,
                error=f"Image CAPTCHA solve error: {str(e)}",
            )
    
    def _preprocess_captcha_image(self, image):
        """Preprocess CAPTCHA image for better OCR results"""
        from PIL import Image, ImageFilter, ImageOps
        
        # Convert to grayscale
        image = image.convert('L')
        
        # Increase contrast
        image = ImageOps.autocontrast(image)
        
        # Apply threshold to create binary image
        threshold = 128
        image = image.point(lambda p: 255 if p > threshold else 0)
        
        # Remove noise
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # Scale up for better OCR
        width, height = image.size
        image = image.resize((width * 2, height * 2), Image.LANCZOS)
        
        return image
    
    async def _simulate_human_behavior(self, page) -> None:
        """Simulate human-like browser behavior"""
        # Random mouse movements
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            await page.mouse.move(x, y, steps=random.randint(10, 30))
            await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Random scrolling
        scroll_amount = random.randint(100, 300)
        await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
        await asyncio.sleep(random.uniform(0.5, 1.0))
        await page.evaluate(f'window.scrollBy(0, -{scroll_amount // 2})')
    
    async def _human_like_click(self, page, box: Dict) -> None:
        """Perform a human-like click on an element"""
        # Calculate a random point within the element
        x = box['x'] + random.uniform(box['width'] * 0.2, box['width'] * 0.8)
        y = box['y'] + random.uniform(box['height'] * 0.2, box['height'] * 0.8)
        
        # Move mouse with natural curve
        await page.mouse.move(x, y, steps=random.randint(20, 40))
        
        # Small delay before clicking
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Click with slight delay
        await page.mouse.down()
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await page.mouse.up()


class CaptchaHandler:
    """
    Main CAPTCHA handling class.
    Combines detection and solving capabilities.
    """
    
    def __init__(self):
        self.detector = CaptchaDetector()
        self.solver = CaptchaSolver()
    
    def detect(self, html: str, headers: Optional[Dict[str, str]] = None) -> Optional[CaptchaChallenge]:
        """Detect CAPTCHA in a page"""
        return self.detector.detect(html, headers)
    
    async def solve(
        self,
        challenge: CaptchaChallenge,
        page=None,
    ) -> CaptchaSolution:
        """Attempt to solve a CAPTCHA challenge"""
        return await self.solver.solve(challenge, page)
    
    async def handle_page(
        self,
        html: str,
        headers: Optional[Dict[str, str]] = None,
        page=None,
    ) -> Tuple[bool, Optional[CaptchaSolution]]:
        """
        Detect and attempt to solve any CAPTCHA on a page.
        
        Returns:
            Tuple of (has_captcha, solution)
        """
        challenge = self.detect(html, headers)
        
        if not challenge:
            return False, None
        
        logger.info(
            "captcha_detected",
            captcha_type=challenge.captcha_type.value,
        )
        
        solution = await self.solve(challenge, page)
        
        logger.info(
            "captcha_solve_attempt",
            captcha_type=challenge.captcha_type.value,
            success=solution.success,
            error=solution.error,
        )
        
        return True, solution


# Singleton instance
captcha_handler = CaptchaHandler()
