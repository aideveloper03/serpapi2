"""
OmniScrape Engine - Contact Extractor
Extracts contact information from web pages
"""

import re
from typing import List, Dict, Set
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from models import ExtractedContacts
from utils import get_logger

logger = get_logger(__name__)


class ContactExtractor:
    """
    Extracts contact information from web pages including:
    - Email addresses
    - Phone numbers
    - Social media links
    - Physical addresses
    """
    
    # Email regex pattern
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )
    
    # Phone number patterns (international)
    PHONE_PATTERNS = [
        re.compile(r'\+?\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'),
        re.compile(r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}'),  # (123) 456-7890
        re.compile(r'\d{3}[-.\s]\d{3}[-.\s]\d{4}'),     # 123-456-7890
        re.compile(r'\+\d{10,15}'),                      # +1234567890
    ]
    
    # Social media domains and their names
    SOCIAL_PLATFORMS = {
        'facebook.com': 'facebook',
        'fb.com': 'facebook',
        'twitter.com': 'twitter',
        'x.com': 'twitter',
        'instagram.com': 'instagram',
        'linkedin.com': 'linkedin',
        'youtube.com': 'youtube',
        'youtu.be': 'youtube',
        'tiktok.com': 'tiktok',
        'pinterest.com': 'pinterest',
        'github.com': 'github',
        'gitlab.com': 'gitlab',
        'reddit.com': 'reddit',
        'discord.gg': 'discord',
        'discord.com': 'discord',
        'telegram.me': 'telegram',
        't.me': 'telegram',
        'whatsapp.com': 'whatsapp',
        'snapchat.com': 'snapchat',
        'medium.com': 'medium',
        'twitch.tv': 'twitch',
        'vimeo.com': 'vimeo',
        'tumblr.com': 'tumblr',
        'flickr.com': 'flickr',
        'dribbble.com': 'dribbble',
        'behance.net': 'behance',
    }
    
    # Address patterns
    ADDRESS_PATTERNS = [
        # US addresses
        re.compile(
            r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl)\.?\s*,?\s*[\w\s]+,?\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?',
            re.IGNORECASE
        ),
        # General street addresses
        re.compile(
            r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)\.?',
            re.IGNORECASE
        ),
    ]
    
    # Emails to exclude (common false positives)
    EMAIL_BLACKLIST = {
        'example@example.com',
        'user@example.com',
        'email@example.com',
        'test@test.com',
        'noreply@',
        'no-reply@',
        'donotreply@',
        'mailer-daemon@',
        'postmaster@',
        'webmaster@',
    }
    
    def __init__(self, html: str, url: str):
        self.html = html
        self.url = url
        self.soup = BeautifulSoup(html, 'lxml')
        self.domain = urlparse(url).netloc
    
    def extract(self) -> ExtractedContacts:
        """Extract all contact information"""
        return ExtractedContacts(
            emails=self._extract_emails(),
            phones=self._extract_phones(),
            social_links=self._extract_social_links(),
            addresses=self._extract_addresses(),
        )
    
    def _extract_emails(self) -> List[str]:
        """Extract email addresses"""
        emails: Set[str] = set()
        
        # Extract from text
        text = self.soup.get_text()
        for match in self.EMAIL_PATTERN.findall(text):
            email = match.lower()
            if self._is_valid_email(email):
                emails.add(email)
        
        # Extract from mailto links
        for link in self.soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('mailto:'):
                email = href[7:].split('?')[0].lower()
                if self._is_valid_email(email):
                    emails.add(email)
        
        # Extract from href attributes that might contain emails
        for elem in self.soup.find_all(href=self.EMAIL_PATTERN):
            href = elem.get('href', '')
            for match in self.EMAIL_PATTERN.findall(href):
                email = match.lower()
                if self._is_valid_email(email):
                    emails.add(email)
        
        return sorted(list(emails))
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate an email address"""
        if not email or '@' not in email:
            return False
        
        # Check blacklist
        for blacklisted in self.EMAIL_BLACKLIST:
            if blacklisted in email:
                return False
        
        # Check for common file extensions (false positives)
        if any(email.endswith(ext) for ext in ['.png', '.jpg', '.gif', '.css', '.js']):
            return False
        
        # Basic format validation
        parts = email.split('@')
        if len(parts) != 2:
            return False
        
        local, domain = parts
        if not local or not domain:
            return False
        
        if '.' not in domain:
            return False
        
        return True
    
    def _extract_phones(self) -> List[str]:
        """Extract phone numbers"""
        phones: Set[str] = set()
        
        text = self.soup.get_text()
        
        for pattern in self.PHONE_PATTERNS:
            for match in pattern.findall(text):
                phone = self._normalize_phone(match)
                if self._is_valid_phone(phone):
                    phones.add(phone)
        
        # Extract from tel: links
        for link in self.soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('tel:'):
                phone = href[4:]
                phone = self._normalize_phone(phone)
                if self._is_valid_phone(phone):
                    phones.add(phone)
        
        # Try using phonenumbers library for better parsing
        try:
            import phonenumbers
            
            for match in phonenumbers.PhoneNumberMatcher(text, "US"):
                phone = phonenumbers.format_number(
                    match.number,
                    phonenumbers.PhoneNumberFormat.E164
                )
                phones.add(phone)
                
        except ImportError:
            pass
        except Exception:
            pass
        
        return sorted(list(phones))
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize a phone number"""
        # Remove common separators but keep +
        normalized = re.sub(r'[\s\-\.\(\)]', '', phone)
        return normalized
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Validate a phone number"""
        # Remove non-digit characters except +
        digits = re.sub(r'[^\d]', '', phone)
        
        # Should have between 7 and 15 digits
        if len(digits) < 7 or len(digits) > 15:
            return False
        
        # Avoid false positives (dates, IDs, etc.)
        if digits.startswith('0000'):
            return False
        
        if digits.startswith('1234'):
            return False
        
        return True
    
    def _extract_social_links(self) -> Dict[str, List[str]]:
        """Extract social media links"""
        social_links: Dict[str, Set[str]] = {}
        
        # Find all links
        for link in self.soup.find_all('a', href=True):
            href = link['href']
            
            try:
                parsed = urlparse(href)
                domain = parsed.netloc.lower()
                
                # Remove www prefix
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                # Check if it's a social platform
                for social_domain, platform_name in self.SOCIAL_PLATFORMS.items():
                    if domain == social_domain or domain.endswith('.' + social_domain):
                        if platform_name not in social_links:
                            social_links[platform_name] = set()
                        
                        # Clean and add the URL
                        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
                        
                        # Skip if it's just the homepage
                        if parsed.path and parsed.path != '/':
                            social_links[platform_name].add(clean_url)
                        break
                        
            except Exception:
                continue
        
        # Also check for social links in meta tags
        for meta in self.soup.find_all('meta'):
            content = meta.get('content', '')
            for social_domain, platform_name in self.SOCIAL_PLATFORMS.items():
                if social_domain in content:
                    if platform_name not in social_links:
                        social_links[platform_name] = set()
                    social_links[platform_name].add(content)
        
        # Convert sets to sorted lists
        return {k: sorted(list(v)) for k, v in social_links.items() if v}
    
    def _extract_addresses(self) -> List[str]:
        """Extract physical addresses"""
        addresses: Set[str] = set()
        
        text = self.soup.get_text()
        
        # Try regex patterns
        for pattern in self.ADDRESS_PATTERNS:
            for match in pattern.findall(text):
                address = self._clean_address(match)
                if address:
                    addresses.add(address)
        
        # Look for address-related elements
        address_elements = self.soup.find_all(
            attrs={'itemprop': re.compile(r'address|streetAddress|locality', re.I)}
        )
        
        for elem in address_elements:
            address = self._clean_address(elem.get_text())
            if address:
                addresses.add(address)
        
        # Look for elements with address-related classes
        for elem in self.soup.find_all(class_=re.compile(r'address|location', re.I)):
            address = self._clean_address(elem.get_text())
            if address and len(address) < 200:  # Sanity check
                addresses.add(address)
        
        return list(addresses)
    
    def _clean_address(self, address: str) -> str:
        """Clean an extracted address"""
        if not address:
            return ""
        
        # Normalize whitespace
        address = re.sub(r'\s+', ' ', address).strip()
        
        # Remove very short addresses
        if len(address) < 10:
            return ""
        
        return address
