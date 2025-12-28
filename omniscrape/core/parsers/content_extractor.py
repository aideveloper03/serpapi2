"""
OmniScrape Engine - Content Extractor
Extracts and categorizes main content from web pages
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup, Tag, NavigableString
import json

from models import ExtractedContent, ContentType
from utils import get_logger

logger = get_logger(__name__)


class ContentExtractor:
    """
    Extracts main content from web pages using multiple strategies:
    1. Article-specific tags (article, main, etc.)
    2. Content density analysis
    3. Schema.org/microdata
    4. Heuristic-based extraction
    """
    
    # Tags that typically contain main content
    CONTENT_TAGS = ['article', 'main', 'section', 'div']
    
    # Tags to remove before extraction
    NOISE_TAGS = [
        'script', 'style', 'noscript', 'iframe', 'svg', 'canvas',
        'nav', 'header', 'footer', 'aside', 'form', 'button',
        'select', 'input', 'textarea', 'advertisement', 'ad',
    ]
    
    # Classes/IDs that indicate non-content areas
    NOISE_PATTERNS = [
        r'comment', r'sidebar', r'widget', r'footer', r'header',
        r'menu', r'nav', r'share', r'social', r'ad', r'promo',
        r'related', r'recommend', r'popup', r'modal', r'cookie',
        r'banner', r'sponsor', r'newsletter',
    ]
    
    # Classes/IDs that indicate content areas
    CONTENT_PATTERNS = [
        r'article', r'content', r'post', r'entry', r'story',
        r'body', r'main', r'text', r'prose',
    ]
    
    def __init__(self, html: str, url: str):
        self.html = html
        self.url = url
        self.soup = BeautifulSoup(html, 'lxml')
        self._clean_soup()
    
    def _clean_soup(self) -> None:
        """Remove noise elements from the soup"""
        # Remove noise tags
        for tag_name in self.NOISE_TAGS:
            for tag in self.soup.find_all(tag_name):
                tag.decompose()
        
        # Remove elements with noise classes/ids
        for element in self.soup.find_all(True):
            classes = ' '.join(element.get('class', []))
            element_id = element.get('id', '')
            combined = f"{classes} {element_id}".lower()
            
            for pattern in self.NOISE_PATTERNS:
                if re.search(pattern, combined):
                    # Don't remove if it also matches content patterns
                    is_content = any(
                        re.search(cp, combined) 
                        for cp in self.CONTENT_PATTERNS
                    )
                    if not is_content:
                        element.decompose()
                        break
    
    def extract(self) -> ExtractedContent:
        """Extract main content from the page"""
        # Try structured data first
        structured_content = self._extract_from_structured_data()
        if structured_content and structured_content.text and len(structured_content.text) > 200:
            return structured_content
        
        # Try article-specific extraction
        article_content = self._extract_from_article()
        if article_content and article_content.text and len(article_content.text) > 200:
            return article_content
        
        # Fall back to content density analysis
        density_content = self._extract_by_density()
        if density_content and density_content.text:
            return density_content
        
        # Last resort: extract all text from body
        return self._extract_fallback()
    
    def _extract_from_structured_data(self) -> Optional[ExtractedContent]:
        """Extract content from Schema.org/JSON-LD data"""
        try:
            # Find JSON-LD scripts
            for script in self.soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    
                    # Handle arrays
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    
                    # Check for article types
                    schema_type = data.get('@type', '')
                    if isinstance(schema_type, list):
                        schema_type = schema_type[0] if schema_type else ''
                    
                    article_types = ['Article', 'NewsArticle', 'BlogPosting', 'WebPage']
                    if schema_type in article_types:
                        return ExtractedContent(
                            title=data.get('headline', data.get('name')),
                            text=self._clean_text(data.get('articleBody', data.get('text', ''))),
                            summary=data.get('description'),
                            authors=self._extract_authors_from_schema(data),
                            publish_date=data.get('datePublished'),
                            content_type=self._determine_content_type(schema_type),
                            language=data.get('inLanguage'),
                            keywords=data.get('keywords', '').split(',') if isinstance(data.get('keywords'), str) else [],
                        )
                        
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.debug("structured_data_extraction_failed", error=str(e))
        
        return None
    
    def _extract_authors_from_schema(self, data: Dict) -> List[str]:
        """Extract author names from schema data"""
        authors = []
        author_data = data.get('author', [])
        
        if isinstance(author_data, dict):
            author_data = [author_data]
        
        for author in author_data:
            if isinstance(author, dict):
                name = author.get('name', '')
                if name:
                    authors.append(name)
            elif isinstance(author, str):
                authors.append(author)
        
        return authors
    
    def _extract_from_article(self) -> Optional[ExtractedContent]:
        """Extract content from article elements"""
        # Try to find the main article element
        article = self.soup.find('article')
        
        if not article:
            # Try common content containers
            for selector in ['main', 'div.article', 'div.post', 'div.content', 'div.entry']:
                if '.' in selector:
                    tag, cls = selector.split('.')
                    article = self.soup.find(tag, class_=cls)
                else:
                    article = self.soup.find(selector)
                if article:
                    break
        
        if not article:
            return None
        
        # Extract title
        title = self._extract_title(article)
        
        # Extract text from paragraphs
        paragraphs = []
        for p in article.find_all(['p', 'div', 'span'], recursive=True):
            text = self._clean_text(p.get_text())
            if text and len(text) > 50:  # Skip short snippets
                paragraphs.append(text)
        
        # Deduplicate paragraphs
        seen = set()
        unique_paragraphs = []
        for p in paragraphs:
            if p not in seen:
                seen.add(p)
                unique_paragraphs.append(p)
        
        text = '\n\n'.join(unique_paragraphs)
        
        # Extract metadata
        authors = self._extract_authors(article)
        publish_date = self._extract_date(article)
        
        # Calculate metrics
        word_count = len(text.split())
        reading_time = max(1, word_count // 200)
        
        return ExtractedContent(
            title=title,
            text=text,
            summary=self._generate_summary(text),
            authors=authors,
            publish_date=publish_date,
            content_type=ContentType.ARTICLE,
            word_count=word_count,
            reading_time_minutes=reading_time,
        )
    
    def _extract_by_density(self) -> Optional[ExtractedContent]:
        """Extract content using text density analysis"""
        # Find the element with highest text density
        best_element = None
        best_score = 0
        
        for element in self.soup.find_all(self.CONTENT_TAGS):
            score = self._calculate_content_score(element)
            if score > best_score:
                best_score = score
                best_element = element
        
        if not best_element or best_score < 100:
            return None
        
        # Extract text
        text = self._extract_text_from_element(best_element)
        
        word_count = len(text.split())
        
        return ExtractedContent(
            title=self._extract_title(best_element) or self._get_page_title(),
            text=text,
            summary=self._generate_summary(text),
            content_type=self._detect_content_type(),
            word_count=word_count,
            reading_time_minutes=max(1, word_count // 200),
        )
    
    def _calculate_content_score(self, element: Tag) -> float:
        """Calculate a content score for an element"""
        text = element.get_text()
        text_length = len(text)
        
        if text_length < 100:
            return 0
        
        # Count paragraphs
        p_count = len(element.find_all('p'))
        
        # Count links (lower is better for content)
        link_count = len(element.find_all('a'))
        link_density = link_count / max(1, text_length / 100)
        
        # Check for content-indicating classes
        classes = ' '.join(element.get('class', []))
        content_bonus = 0
        for pattern in self.CONTENT_PATTERNS:
            if re.search(pattern, classes, re.IGNORECASE):
                content_bonus += 50
        
        # Calculate score
        score = (
            text_length * 0.1 +
            p_count * 20 +
            content_bonus -
            link_density * 50
        )
        
        return max(0, score)
    
    def _extract_text_from_element(self, element: Tag) -> str:
        """Extract clean text from an element"""
        paragraphs = []
        
        for tag in element.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
            text = self._clean_text(tag.get_text())
            if text and len(text) > 20:
                paragraphs.append(text)
        
        return '\n\n'.join(paragraphs)
    
    def _extract_fallback(self) -> ExtractedContent:
        """Fallback extraction: get all body text"""
        body = self.soup.find('body')
        if not body:
            return ExtractedContent(
                title=self._get_page_title(),
                content_type=ContentType.UNKNOWN,
            )
        
        text = self._clean_text(body.get_text())
        word_count = len(text.split())
        
        return ExtractedContent(
            title=self._get_page_title(),
            text=text[:10000],  # Limit length
            summary=self._generate_summary(text),
            content_type=self._detect_content_type(),
            word_count=word_count,
            reading_time_minutes=max(1, word_count // 200),
        )
    
    def _extract_title(self, context: Optional[Tag] = None) -> Optional[str]:
        """Extract article title"""
        search_in = context or self.soup
        
        # Try h1 first
        h1 = search_in.find('h1')
        if h1:
            return self._clean_text(h1.get_text())
        
        # Try title tag
        return self._get_page_title()
    
    def _get_page_title(self) -> Optional[str]:
        """Get the page title"""
        title_tag = self.soup.find('title')
        if title_tag:
            title = self._clean_text(title_tag.get_text())
            # Remove site name suffix
            title = re.sub(r'\s*[|\-–—]\s*[^|\-–—]+$', '', title)
            return title
        return None
    
    def _extract_authors(self, context: Optional[Tag] = None) -> List[str]:
        """Extract author names"""
        authors = []
        search_in = context or self.soup
        
        # Common author selectors
        selectors = [
            '[rel="author"]',
            '[itemprop="author"]',
            '.author',
            '.byline',
            '.author-name',
            '.writer',
        ]
        
        for selector in selectors:
            elements = search_in.select(selector)
            for elem in elements:
                name = self._clean_text(elem.get_text())
                if name and len(name) < 100:  # Sanity check
                    authors.append(name)
        
        # Deduplicate
        return list(dict.fromkeys(authors))
    
    def _extract_date(self, context: Optional[Tag] = None) -> Optional[str]:
        """Extract publication date"""
        search_in = context or self.soup
        
        # Try time element
        time_elem = search_in.find('time')
        if time_elem:
            datetime_attr = time_elem.get('datetime')
            if datetime_attr:
                return datetime_attr
            return self._clean_text(time_elem.get_text())
        
        # Try meta tags
        for meta in self.soup.find_all('meta'):
            prop = meta.get('property', '') + meta.get('name', '')
            if any(x in prop.lower() for x in ['published', 'date', 'time']):
                content = meta.get('content')
                if content:
                    return content
        
        return None
    
    def _generate_summary(self, text: str, max_length: int = 300) -> Optional[str]:
        """Generate a summary from the text"""
        if not text:
            return None
        
        # Get first paragraph or sentence
        paragraphs = text.split('\n')
        for p in paragraphs:
            p = p.strip()
            if len(p) > 50:
                if len(p) > max_length:
                    # Cut at sentence boundary
                    sentences = re.split(r'[.!?]\s+', p)
                    summary = ""
                    for s in sentences:
                        if len(summary) + len(s) < max_length:
                            summary += s + ". "
                        else:
                            break
                    return summary.strip() or p[:max_length] + "..."
                return p
        
        return text[:max_length] + "..." if len(text) > max_length else text
    
    def _detect_content_type(self) -> ContentType:
        """Detect the type of content on the page"""
        html_lower = self.html.lower()
        url_lower = self.url.lower()
        
        # Check URL patterns
        if any(x in url_lower for x in ['/news/', '/article/', '/story/']):
            return ContentType.NEWS
        if any(x in url_lower for x in ['/blog/', '/post/']):
            return ContentType.BLOG
        if any(x in url_lower for x in ['/product/', '/item/', '/shop/']):
            return ContentType.PRODUCT
        if any(x in url_lower for x in ['/forum/', '/thread/', '/discussion/']):
            return ContentType.FORUM
        
        # Check page content
        if self.soup.find('article'):
            return ContentType.ARTICLE
        
        # Check for product indicators
        if self.soup.find(attrs={'itemprop': 'price'}):
            return ContentType.PRODUCT
        
        return ContentType.UNKNOWN
    
    def _determine_content_type(self, schema_type: str) -> ContentType:
        """Determine content type from schema type"""
        type_map = {
            'NewsArticle': ContentType.NEWS,
            'BlogPosting': ContentType.BLOG,
            'Article': ContentType.ARTICLE,
            'Product': ContentType.PRODUCT,
            'DiscussionForumPosting': ContentType.FORUM,
        }
        return type_map.get(schema_type, ContentType.UNKNOWN)
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ""
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
