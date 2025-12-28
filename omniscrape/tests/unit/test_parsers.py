"""
Unit tests for content parsers
"""

import pytest
from core.parsers.content_extractor import ContentExtractor
from core.parsers.contact_extractor import ContactExtractor
from core.parsers.metadata_extractor import MetadataExtractor


class TestContentExtractor:
    """Tests for ContentExtractor"""
    
    def test_extract_title_from_h1(self):
        """Test title extraction from h1 tag"""
        html = """
        <html>
            <head><title>Page Title | Site Name</title></head>
            <body>
                <article>
                    <h1>Article Title</h1>
                    <p>Article content goes here.</p>
                </article>
            </body>
        </html>
        """
        extractor = ContentExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert result.title == "Article Title"
    
    def test_extract_content_from_article(self):
        """Test content extraction from article tag"""
        html = """
        <html>
            <body>
                <nav>Navigation links</nav>
                <article>
                    <h1>Main Article</h1>
                    <p>This is the first paragraph with substantial content that should be extracted.</p>
                    <p>This is the second paragraph with more content for the article.</p>
                </article>
                <footer>Footer content</footer>
            </body>
        </html>
        """
        extractor = ContentExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert result.text is not None
        assert "first paragraph" in result.text
        assert "second paragraph" in result.text
        assert "Navigation" not in result.text
        assert "Footer" not in result.text
    
    def test_word_count_calculation(self):
        """Test word count is calculated correctly"""
        html = """
        <article>
            <p>One two three four five six seven eight nine ten.</p>
        </article>
        """
        extractor = ContentExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert result.word_count >= 10
    
    def test_extract_from_schema_org(self):
        """Test extraction from JSON-LD structured data"""
        html = """
        <html>
            <head>
                <script type="application/ld+json">
                {
                    "@type": "Article",
                    "headline": "Schema Article Title",
                    "articleBody": "This is the article body from schema.org markup.",
                    "author": {"@type": "Person", "name": "John Doe"}
                }
                </script>
            </head>
            <body></body>
        </html>
        """
        extractor = ContentExtractor(html, "https://example.com")
        result = extractor.extract()
        
        # Should extract from schema
        assert result.title == "Schema Article Title" or result.title is None


class TestContactExtractor:
    """Tests for ContactExtractor"""
    
    def test_extract_email(self):
        """Test email extraction"""
        html = """
        <html>
            <body>
                <p>Contact us at contact@example.com or support@example.org</p>
            </body>
        </html>
        """
        extractor = ContactExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert "contact@example.com" in result.emails
        assert "support@example.org" in result.emails
    
    def test_extract_mailto_links(self):
        """Test email extraction from mailto links"""
        html = """
        <html>
            <body>
                <a href="mailto:sales@example.com">Email Sales</a>
            </body>
        </html>
        """
        extractor = ContactExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert "sales@example.com" in result.emails
    
    def test_filter_invalid_emails(self):
        """Test that invalid emails are filtered"""
        html = """
        <html>
            <body>
                <p>Invalid: test@test.png, noreply@example.com</p>
            </body>
        </html>
        """
        extractor = ContactExtractor(html, "https://example.com")
        result = extractor.extract()
        
        # Should filter out file extensions and noreply
        assert not any("test@test.png" in e for e in result.emails)
    
    def test_extract_phone_numbers(self):
        """Test phone number extraction"""
        html = """
        <html>
            <body>
                <p>Call us at (555) 123-4567 or +1-555-987-6543</p>
            </body>
        </html>
        """
        extractor = ContactExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert len(result.phones) >= 1
    
    def test_extract_social_links(self):
        """Test social media link extraction"""
        html = """
        <html>
            <body>
                <a href="https://twitter.com/example">Twitter</a>
                <a href="https://www.facebook.com/example">Facebook</a>
                <a href="https://www.linkedin.com/company/example">LinkedIn</a>
            </body>
        </html>
        """
        extractor = ContactExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert "twitter" in result.social_links
        assert "facebook" in result.social_links
        assert "linkedin" in result.social_links


class TestMetadataExtractor:
    """Tests for MetadataExtractor"""
    
    def test_extract_title(self):
        """Test title extraction"""
        html = """
        <html>
            <head>
                <title>Page Title | Site Name</title>
            </head>
        </html>
        """
        extractor = MetadataExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert "Page Title" in result.title
    
    def test_extract_meta_description(self):
        """Test meta description extraction"""
        html = """
        <html>
            <head>
                <meta name="description" content="This is the meta description.">
            </head>
        </html>
        """
        extractor = MetadataExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert result.description == "This is the meta description."
    
    def test_extract_opengraph(self):
        """Test OpenGraph metadata extraction"""
        html = """
        <html>
            <head>
                <meta property="og:title" content="OG Title">
                <meta property="og:description" content="OG Description">
                <meta property="og:image" content="https://example.com/image.jpg">
            </head>
        </html>
        """
        extractor = MetadataExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert result.og_data.get("title") == "OG Title"
        assert result.og_data.get("description") == "OG Description"
        assert result.og_data.get("image") == "https://example.com/image.jpg"
    
    def test_extract_twitter_cards(self):
        """Test Twitter Card metadata extraction"""
        html = """
        <html>
            <head>
                <meta name="twitter:card" content="summary_large_image">
                <meta name="twitter:title" content="Twitter Title">
            </head>
        </html>
        """
        extractor = MetadataExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert result.twitter_data.get("card") == "summary_large_image"
        assert result.twitter_data.get("title") == "Twitter Title"
    
    def test_extract_canonical_url(self):
        """Test canonical URL extraction"""
        html = """
        <html>
            <head>
                <link rel="canonical" href="https://example.com/page">
            </head>
        </html>
        """
        extractor = MetadataExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert result.canonical_url == "https://example.com/page"
    
    def test_extract_json_ld(self):
        """Test JSON-LD structured data extraction"""
        html = """
        <html>
            <head>
                <script type="application/ld+json">
                {
                    "@type": "Organization",
                    "name": "Example Corp",
                    "url": "https://example.com"
                }
                </script>
            </head>
        </html>
        """
        extractor = MetadataExtractor(html, "https://example.com")
        result = extractor.extract()
        
        assert len(result.structured_data) > 0
        assert result.structured_data[0].get("@type") == "Organization"
