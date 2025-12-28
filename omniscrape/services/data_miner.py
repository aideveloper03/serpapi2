"""
OmniScrape Engine - Data Mining Service
Bulk data extraction and intelligence gathering
"""

import asyncio
import re
from typing import Optional, List, Dict, Any, Set
from urllib.parse import urlparse
from dataclasses import dataclass, field
from datetime import datetime

from config import settings
from utils import get_logger
from core.parsers import ContentExtractor, ContactExtractor, MetadataExtractor
from services.network_client import network_client

logger = get_logger(__name__)


@dataclass
class CompanyProfile:
    """Extracted company information"""
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    founded: Optional[str] = None
    headquarters: Optional[str] = None
    social_profiles: Dict[str, str] = field(default_factory=dict)
    contact_emails: List[str] = field(default_factory=list)
    contact_phones: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)


@dataclass
class WebsiteIntelligence:
    """Intelligence gathered from a website"""
    url: str
    domain: str
    title: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    company: Optional[CompanyProfile] = None
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    social_links: Dict[str, List[str]] = field(default_factory=dict)
    technologies: List[str] = field(default_factory=list)
    internal_pages: List[str] = field(default_factory=list)
    external_links: List[str] = field(default_factory=list)
    structured_data: List[Dict] = field(default_factory=list)
    gathered_at: datetime = field(default_factory=datetime.utcnow)


class TechnologyDetector:
    """
    Detects technologies used on websites based on signatures.
    """
    
    SIGNATURES = {
        # JavaScript Frameworks
        'React': [
            r'react\.production\.min\.js',
            r'react-dom',
            r'__REACT',
            r'data-reactroot',
        ],
        'Vue.js': [
            r'vue\.runtime',
            r'vue\.min\.js',
            r'__vue__',
            r'v-bind:',
        ],
        'Angular': [
            r'angular\.min\.js',
            r'ng-version',
            r'ng-controller',
        ],
        'jQuery': [
            r'jquery\.min\.js',
            r'jquery-\d+\.\d+',
        ],
        
        # CMS
        'WordPress': [
            r'wp-content',
            r'wp-includes',
            r'WordPress',
        ],
        'Drupal': [
            r'Drupal\.settings',
            r'/sites/default/',
        ],
        'Shopify': [
            r'cdn\.shopify\.com',
            r'Shopify\.theme',
        ],
        'Wix': [
            r'wix\.com',
            r'wixstatic\.com',
        ],
        
        # Analytics
        'Google Analytics': [
            r'google-analytics\.com',
            r'googletagmanager\.com',
            r'gtag\(',
        ],
        'Facebook Pixel': [
            r'connect\.facebook\.net',
            r'fbq\(',
        ],
        'Hotjar': [
            r'hotjar\.com',
        ],
        
        # CDN
        'Cloudflare': [
            r'cloudflare',
            r'cf-ray',
        ],
        'Fastly': [
            r'fastly\.net',
        ],
        'AWS CloudFront': [
            r'cloudfront\.net',
        ],
        
        # Other
        'Bootstrap': [
            r'bootstrap\.min',
            r'bootstrap\.css',
        ],
        'Tailwind CSS': [
            r'tailwindcss',
            r'tailwind\.min',
        ],
        'Next.js': [
            r'_next/static',
            r'__NEXT_DATA__',
        ],
        'Nuxt.js': [
            r'_nuxt/',
            r'__NUXT__',
        ],
    }
    
    def detect(self, html: str, headers: Dict[str, str] = None) -> List[str]:
        """Detect technologies in HTML and headers"""
        detected = []
        
        # Check HTML signatures
        for tech, patterns in self.SIGNATURES.items():
            for pattern in patterns:
                if re.search(pattern, html, re.IGNORECASE):
                    if tech not in detected:
                        detected.append(tech)
                    break
        
        # Check headers
        if headers:
            header_str = str(headers).lower()
            if 'cloudflare' in header_str:
                if 'Cloudflare' not in detected:
                    detected.append('Cloudflare')
            if 'x-powered-by' in header_str:
                powered_by = headers.get('X-Powered-By', headers.get('x-powered-by', ''))
                if powered_by and powered_by not in detected:
                    detected.append(powered_by)
        
        return sorted(detected)


class DataMiner:
    """
    Comprehensive data mining service for websites.
    Extracts business intelligence from target URLs.
    """
    
    def __init__(self):
        self._tech_detector = TechnologyDetector()
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_deep_scrapes)
    
    async def gather_intelligence(
        self,
        url: str,
        deep_scan: bool = False,
    ) -> WebsiteIntelligence:
        """
        Gather comprehensive intelligence from a website.
        
        Args:
            url: Target URL
            deep_scan: If True, also crawl contact/about pages
        
        Returns:
            WebsiteIntelligence object with extracted data
        """
        async with self._semaphore:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            logger.info("gathering_intelligence", url=url, deep_scan=deep_scan)
            
            # Fetch main page
            try:
                status, html, headers = await network_client.get(url)
                
                if status != 200:
                    return WebsiteIntelligence(url=url, domain=domain)
                
            except Exception as e:
                logger.error("intelligence_fetch_error", url=url, error=str(e))
                return WebsiteIntelligence(url=url, domain=domain)
            
            # Extract data using parsers
            content = ContentExtractor(html, url).extract()
            contacts = ContactExtractor(html, url).extract()
            metadata = MetadataExtractor(html, url).extract()
            
            # Detect technologies
            technologies = self._tech_detector.detect(html, headers)
            
            # Extract company profile from structured data
            company = self._extract_company_profile(metadata.structured_data)
            
            # Create intelligence object
            intel = WebsiteIntelligence(
                url=url,
                domain=domain,
                title=metadata.title,
                description=metadata.description,
                language=metadata.language,
                company=company,
                emails=contacts.emails,
                phones=contacts.phones,
                social_links=contacts.social_links,
                technologies=technologies,
                structured_data=metadata.structured_data,
            )
            
            # Deep scan: crawl additional pages
            if deep_scan:
                intel = await self._deep_scan(intel, html, url)
            
            logger.info(
                "intelligence_gathered",
                url=url,
                emails_found=len(intel.emails),
                phones_found=len(intel.phones),
                technologies=len(intel.technologies),
            )
            
            return intel
    
    def _extract_company_profile(self, structured_data: List[Dict]) -> Optional[CompanyProfile]:
        """Extract company profile from structured data"""
        for item in structured_data:
            if not isinstance(item, dict):
                continue
            
            item_type = item.get('@type', '')
            
            if item_type in ['Organization', 'Corporation', 'LocalBusiness', 'Company']:
                return CompanyProfile(
                    name=item.get('name'),
                    description=item.get('description'),
                    website=item.get('url'),
                    logo_url=item.get('logo'),
                    founded=item.get('foundingDate'),
                    headquarters=str(item.get('address', '')),
                )
        
        return None
    
    async def _deep_scan(
        self,
        intel: WebsiteIntelligence,
        html: str,
        base_url: str,
    ) -> WebsiteIntelligence:
        """Perform deep scan of additional pages"""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Find contact and about pages
        important_pages = []
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()
            
            if any(kw in href or kw in text for kw in ['contact', 'about', 'team', 'company']):
                full_url = urljoin(base_url, link['href'])
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    important_pages.append(full_url)
        
        # Deduplicate
        important_pages = list(set(important_pages))[:5]
        
        # Fetch and extract from each page
        all_emails = set(intel.emails)
        all_phones = set(intel.phones)
        
        for page_url in important_pages:
            try:
                status, page_html, _ = await network_client.get(page_url)
                if status == 200:
                    page_contacts = ContactExtractor(page_html, page_url).extract()
                    all_emails.update(page_contacts.emails)
                    all_phones.update(page_contacts.phones)
                    
                    # Merge social links
                    for platform, links in page_contacts.social_links.items():
                        if platform not in intel.social_links:
                            intel.social_links[platform] = []
                        intel.social_links[platform].extend(links)
                
                await asyncio.sleep(0.5)  # Polite delay
                
            except Exception as e:
                logger.debug("deep_scan_page_error", url=page_url, error=str(e))
        
        intel.emails = sorted(list(all_emails))
        intel.phones = sorted(list(all_phones))
        intel.internal_pages = important_pages
        
        # Deduplicate social links
        for platform in intel.social_links:
            intel.social_links[platform] = sorted(list(set(intel.social_links[platform])))
        
        return intel
    
    async def bulk_gather(
        self,
        urls: List[str],
        deep_scan: bool = False,
        parallel: bool = True,
    ) -> List[WebsiteIntelligence]:
        """
        Gather intelligence from multiple URLs.
        
        Args:
            urls: List of URLs to process
            deep_scan: Enable deep scanning
            parallel: Process URLs in parallel
        
        Returns:
            List of WebsiteIntelligence objects
        """
        if parallel:
            tasks = [self.gather_intelligence(url, deep_scan) for url in urls]
            return await asyncio.gather(*tasks, return_exceptions=False)
        else:
            results = []
            for url in urls:
                result = await self.gather_intelligence(url, deep_scan)
                results.append(result)
            return results


# Singleton instance
data_miner = DataMiner()
