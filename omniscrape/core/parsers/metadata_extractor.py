"""
OmniScrape Engine - Metadata Extractor
Extracts metadata and structured data from web pages
"""

import re
import json
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from models import ExtractedMetadata
from utils import get_logger

logger = get_logger(__name__)


class MetadataExtractor:
    """
    Extracts metadata from web pages including:
    - Basic meta tags (title, description, keywords)
    - Open Graph data
    - Twitter Card data
    - Schema.org structured data (JSON-LD, microdata)
    - Other relevant meta information
    """
    
    def __init__(self, html: str, url: str):
        self.html = html
        self.url = url
        self.soup = BeautifulSoup(html, 'lxml')
    
    def extract(self) -> ExtractedMetadata:
        """Extract all metadata"""
        return ExtractedMetadata(
            title=self._extract_title(),
            description=self._extract_description(),
            keywords=self._extract_keywords(),
            canonical_url=self._extract_canonical(),
            og_data=self._extract_opengraph(),
            twitter_data=self._extract_twitter_cards(),
            structured_data=self._extract_structured_data(),
            favicon=self._extract_favicon(),
            language=self._extract_language(),
            charset=self._extract_charset(),
        )
    
    def _extract_title(self) -> Optional[str]:
        """Extract page title"""
        # Try og:title first (usually cleaner)
        og_title = self._get_meta_content('og:title')
        if og_title:
            return og_title
        
        # Try twitter:title
        twitter_title = self._get_meta_content('twitter:title')
        if twitter_title:
            return twitter_title
        
        # Try title tag
        title_tag = self.soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            # Remove site name suffix
            title = re.sub(r'\s*[|\-–—]\s*[^|\-–—]+$', '', title)
            return title
        
        return None
    
    def _extract_description(self) -> Optional[str]:
        """Extract page description"""
        # Try multiple sources
        sources = [
            ('meta', {'name': 'description'}),
            ('meta', {'property': 'og:description'}),
            ('meta', {'name': 'twitter:description'}),
        ]
        
        for tag, attrs in sources:
            elem = self.soup.find(tag, attrs)
            if elem:
                content = elem.get('content', '')
                if content:
                    return content.strip()
        
        return None
    
    def _extract_keywords(self) -> List[str]:
        """Extract keywords"""
        keywords = []
        
        # Try meta keywords
        meta_keywords = self._get_meta_content('keywords', attr='name')
        if meta_keywords:
            # Split by comma
            keywords.extend([k.strip() for k in meta_keywords.split(',') if k.strip()])
        
        # Try article:tag
        for meta in self.soup.find_all('meta', property='article:tag'):
            tag = meta.get('content', '').strip()
            if tag:
                keywords.append(tag)
        
        # Deduplicate
        return list(dict.fromkeys(keywords))
    
    def _extract_canonical(self) -> Optional[str]:
        """Extract canonical URL"""
        link = self.soup.find('link', rel='canonical')
        if link:
            return link.get('href')
        
        og_url = self._get_meta_content('og:url')
        if og_url:
            return og_url
        
        return None
    
    def _extract_opengraph(self) -> Dict[str, str]:
        """Extract Open Graph metadata"""
        og_data = {}
        
        og_properties = [
            'og:title', 'og:description', 'og:image', 'og:url', 'og:type',
            'og:site_name', 'og:locale', 'og:image:width', 'og:image:height',
            'og:image:alt', 'og:video', 'og:audio', 'og:determiner',
            'article:author', 'article:published_time', 'article:modified_time',
            'article:section', 'article:tag',
        ]
        
        for prop in og_properties:
            content = self._get_meta_content(prop)
            if content:
                # Use property name without og: prefix
                key = prop.replace('og:', '').replace('article:', 'article_')
                og_data[key] = content
        
        return og_data
    
    def _extract_twitter_cards(self) -> Dict[str, str]:
        """Extract Twitter Card metadata"""
        twitter_data = {}
        
        twitter_properties = [
            'twitter:card', 'twitter:site', 'twitter:creator', 'twitter:title',
            'twitter:description', 'twitter:image', 'twitter:image:alt',
            'twitter:player', 'twitter:player:width', 'twitter:player:height',
        ]
        
        for prop in twitter_properties:
            content = self._get_meta_content(prop, attr='name')
            if not content:
                content = self._get_meta_content(prop)
            if content:
                key = prop.replace('twitter:', '')
                twitter_data[key] = content
        
        return twitter_data
    
    def _extract_structured_data(self) -> List[Dict[str, Any]]:
        """Extract Schema.org structured data (JSON-LD)"""
        structured_data = []
        
        # Extract JSON-LD
        for script in self.soup.find_all('script', type='application/ld+json'):
            try:
                content = script.string
                if content:
                    data = json.loads(content)
                    if isinstance(data, list):
                        structured_data.extend(data)
                    else:
                        structured_data.append(data)
            except json.JSONDecodeError:
                continue
        
        # Extract microdata (simplified)
        microdata = self._extract_microdata()
        if microdata:
            structured_data.append(microdata)
        
        return structured_data
    
    def _extract_microdata(self) -> Optional[Dict[str, Any]]:
        """Extract microdata schema"""
        items = []
        
        for itemscope in self.soup.find_all(attrs={'itemscope': True}):
            item = {}
            
            # Get item type
            itemtype = itemscope.get('itemtype', '')
            if itemtype:
                item['@type'] = itemtype.split('/')[-1]
            
            # Get properties
            for prop in itemscope.find_all(attrs={'itemprop': True}):
                prop_name = prop.get('itemprop')
                
                # Get value based on tag type
                if prop.name in ['a', 'link']:
                    value = prop.get('href')
                elif prop.name == 'img':
                    value = prop.get('src')
                elif prop.name == 'meta':
                    value = prop.get('content')
                elif prop.name == 'time':
                    value = prop.get('datetime') or prop.get_text().strip()
                else:
                    value = prop.get_text().strip()
                
                if value:
                    item[prop_name] = value
            
            if len(item) > 1:  # Has more than just @type
                items.append(item)
        
        if items:
            return {'@type': 'ItemList', 'items': items}
        return None
    
    def _extract_favicon(self) -> Optional[str]:
        """Extract favicon URL"""
        # Try various favicon link types
        selectors = [
            {'rel': 'icon'},
            {'rel': 'shortcut icon'},
            {'rel': 'apple-touch-icon'},
            {'rel': 'apple-touch-icon-precomposed'},
        ]
        
        for selector in selectors:
            link = self.soup.find('link', selector)
            if link:
                href = link.get('href')
                if href:
                    return urljoin(self.url, href)
        
        # Default favicon location
        return urljoin(self.url, '/favicon.ico')
    
    def _extract_language(self) -> Optional[str]:
        """Extract page language"""
        # Try html lang attribute
        html_tag = self.soup.find('html')
        if html_tag:
            lang = html_tag.get('lang')
            if lang:
                return lang
        
        # Try meta tags
        language = self._get_meta_content('language', attr='name')
        if language:
            return language
        
        language = self._get_meta_content('og:locale')
        if language:
            return language
        
        # Try Content-Language header (not available in HTML)
        meta_lang = self.soup.find('meta', attrs={'http-equiv': 'Content-Language'})
        if meta_lang:
            return meta_lang.get('content')
        
        return None
    
    def _extract_charset(self) -> Optional[str]:
        """Extract character encoding"""
        # Try meta charset
        meta_charset = self.soup.find('meta', charset=True)
        if meta_charset:
            return meta_charset.get('charset')
        
        # Try meta http-equiv Content-Type
        meta_ct = self.soup.find('meta', attrs={'http-equiv': 'Content-Type'})
        if meta_ct:
            content = meta_ct.get('content', '')
            match = re.search(r'charset=([^\s;]+)', content, re.I)
            if match:
                return match.group(1)
        
        return 'utf-8'  # Default
    
    def _get_meta_content(
        self,
        value: str,
        attr: str = 'property'
    ) -> Optional[str]:
        """Get meta tag content by property or name"""
        meta = self.soup.find('meta', attrs={attr: value})
        if meta:
            return meta.get('content', '').strip()
        
        # Try alternate attribute
        alt_attr = 'name' if attr == 'property' else 'property'
        meta = self.soup.find('meta', attrs={alt_attr: value})
        if meta:
            return meta.get('content', '').strip()
        
        return None
