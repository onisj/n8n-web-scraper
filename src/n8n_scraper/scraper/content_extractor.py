"""
Content extraction utilities for web scraping.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag, NavigableString
from bs4.element import Comment

from ..core.exceptions import ContentExtractionError
from ..core.logging_config import get_logger
from ..core.metrics import metrics, timing_decorator

logger = get_logger(__name__)


@dataclass
class ExtractedContent:
    """Extracted content from a web page."""
    title: str = ""
    main_content: str = ""
    description: str = ""
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    language: str = "en"
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    breadcrumbs: List[str] = field(default_factory=list)
    headings: List[Dict[str, str]] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    code_blocks: List[Dict[str, str]] = field(default_factory=list)
    tables: List[str] = field(default_factory=list)
    lists: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    word_count: int = 0
    reading_time_minutes: int = 0
    content_hash: Optional[str] = None
    
    def __post_init__(self):
        """Calculate derived fields."""
        if self.main_content:
            self.word_count = len(self.main_content.split())
            # Estimate reading time (average 200 words per minute)
            self.reading_time_minutes = max(1, self.word_count // 200)


class ContentExtractor:
    """Extracts and cleans content from HTML pages."""
    
    def __init__(self):
        """Initialize content extractor."""
        # Common selectors for different content types
        self.content_selectors = [
            # Main content areas
            'main',
            'article',
            '[role="main"]',
            '.main-content',
            '.content',
            '.post-content',
            '.entry-content',
            '.article-content',
            '.documentation',
            '.docs-content',
            
            # Documentation specific
            '.markdown-body',
            '.rst-content',
            '.doc-content',
            '.guide-content',
            
            # Fallback selectors
            'body',
        ]
        
        # Selectors to remove (noise)
        self.noise_selectors = [
            'nav',
            'header',
            'footer',
            'aside',
            '.sidebar',
            '.navigation',
            '.menu',
            '.breadcrumb',
            '.pagination',
            '.comments',
            '.social-share',
            '.advertisement',
            '.ads',
            '.popup',
            '.modal',
            '.cookie-notice',
            '.newsletter',
            'script',
            'style',
            'noscript',
            '.hidden',
            '[style*="display: none"]',
            '[style*="visibility: hidden"]',
        ]
        
        # Date patterns for extraction
        self.date_patterns = [
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\d{2})/(\d{2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{2})\.(\d{2})\.(\d{4})',  # DD.MM.YYYY
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # Month DD, YYYY
        ]
    
    @timing_decorator("content_extractor_extract")
    def extract(self, html: str, url: str) -> ExtractedContent:
        """Extract content from HTML.
        
        Args:
            html: Raw HTML content
            url: Source URL
        
        Returns:
            Extracted content
        
        Raises:
            ContentExtractionError: If extraction fails
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove noise elements
            self._remove_noise(soup)
            
            # Extract different content components
            content = ExtractedContent()
            
            content.title = self._extract_title(soup)
            content.description = self._extract_description(soup)
            content.main_content = self._extract_main_content(soup)
            content.author = self._extract_author(soup)
            content.published_date = self._extract_published_date(soup)
            content.modified_date = self._extract_modified_date(soup)
            content.language = self._extract_language(soup)
            content.tags = self._extract_tags(soup)
            content.categories = self._extract_categories(soup)
            content.breadcrumbs = self._extract_breadcrumbs(soup)
            content.headings = self._extract_headings(soup)
            content.links = self._extract_links(soup, url)
            content.images = self._extract_images(soup, url)
            content.code_blocks = self._extract_code_blocks(soup)
            content.tables = self._extract_tables(soup)
            content.lists = self._extract_lists(soup)
            content.metadata = self._extract_metadata(soup)
            
            # Calculate content hash
            content.content_hash = self._calculate_content_hash(content.main_content)
            
            metrics.increment_counter("content_extractor_success")
            return content
            
        except Exception as e:
            metrics.increment_counter("content_extractor_errors")
            logger.error(f"Content extraction failed for {url}: {e}")
            raise ContentExtractionError(f"Failed to extract content: {str(e)}") from e
    
    def _remove_noise(self, soup: BeautifulSoup) -> None:
        """Remove noise elements from soup.
        
        Args:
            soup: BeautifulSoup object to clean
        """
        for selector in self.noise_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            Page title
        """
        # Try different title sources in order of preference
        title_selectors = [
            'h1',
            'title',
            '[property="og:title"]',
            '[name="twitter:title"]',
            '.page-title',
            '.post-title',
            '.article-title',
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get('content') if element.name == 'meta' else element.get_text()
                if title and title.strip():
                    return title.strip()
        
        return ""
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract page description.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            Page description
        """
        # Try meta descriptions first
        meta_selectors = [
            '[name="description"]',
            '[property="og:description"]',
            '[name="twitter:description"]',
        ]
        
        for selector in meta_selectors:
            element = soup.select_one(selector)
            if element and element.get('content'):
                return element.get('content').strip()
        
        # Fallback to first paragraph
        first_p = soup.select_one('p')
        if first_p:
            text = first_p.get_text().strip()
            if len(text) > 50:  # Only use if substantial
                return text[:300] + '...' if len(text) > 300 else text
        
        return ""
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            Main content text
        """
        # Try content selectors in order of preference
        for selector in self.content_selectors:
            elements = soup.select(selector)
            if elements:
                # Use the first matching element
                content_element = elements[0]
                
                # Clean and extract text
                text = self._clean_text(content_element.get_text())
                
                # Only use if substantial content
                if len(text.split()) > 20:
                    return text
        
        # Fallback: extract all text from body
        body = soup.find('body')
        if body:
            return self._clean_text(body.get_text())
        
        return ""
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author information.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            Author name or None
        """
        author_selectors = [
            '[name="author"]',
            '[property="article:author"]',
            '[rel="author"]',
            '.author',
            '.byline',
            '.post-author',
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get('content') or element.get_text()
                if author and author.strip():
                    return author.strip()
        
        return None
    
    def _extract_published_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract published date.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            Published date or None
        """
        date_selectors = [
            '[property="article:published_time"]',
            '[name="date"]',
            '[name="publish_date"]',
            'time[datetime]',
            '.publish-date',
            '.post-date',
        ]
        
        return self._extract_date(soup, date_selectors)
    
    def _extract_modified_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract modified date.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            Modified date or None
        """
        date_selectors = [
            '[property="article:modified_time"]',
            '[name="last-modified"]',
            '[name="updated"]',
            '.modified-date',
            '.updated-date',
        ]
        
        return self._extract_date(soup, date_selectors)
    
    def _extract_date(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[datetime]:
        """Extract date from selectors.
        
        Args:
            soup: BeautifulSoup object
            selectors: List of CSS selectors to try
        
        Returns:
            Extracted date or None
        """
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                date_str = element.get('content') or element.get('datetime') or element.get_text()
                if date_str:
                    parsed_date = self._parse_date(date_str.strip())
                    if parsed_date:
                        return parsed_date
        
        return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string.
        
        Args:
            date_str: Date string to parse
        
        Returns:
            Parsed datetime or None
        """
        # Try ISO format first
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        # Try common patterns
        for pattern in self.date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if len(match.groups()) == 3:
                        if pattern.startswith(r'(\d{4})'):
                            # YYYY-MM-DD
                            year, month, day = match.groups()
                            return datetime(int(year), int(month), int(day))
                        elif pattern.startswith(r'(\d{2})/(\d{2})'):
                            # MM/DD/YYYY
                            month, day, year = match.groups()
                            return datetime(int(year), int(month), int(day))
                        elif pattern.startswith(r'(\d{2})\.(\d{2})'):
                            # DD.MM.YYYY
                            day, month, year = match.groups()
                            return datetime(int(year), int(month), int(day))
                except ValueError:
                    continue
        
        return None
    
    def _extract_language(self, soup: BeautifulSoup) -> str:
        """Extract page language.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            Language code
        """
        # Check html lang attribute
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            return html_tag.get('lang')[:2].lower()  # Get first 2 chars
        
        # Check meta tags
        meta_lang = soup.select_one('[http-equiv="content-language"]')
        if meta_lang and meta_lang.get('content'):
            return meta_lang.get('content')[:2].lower()
        
        return "en"  # Default to English
    
    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract tags/keywords.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            List of tags
        """
        tags = []
        
        # Meta keywords
        keywords_meta = soup.select_one('[name="keywords"]')
        if keywords_meta and keywords_meta.get('content'):
            keywords = keywords_meta.get('content').split(',')
            tags.extend([tag.strip() for tag in keywords if tag.strip()])
        
        # Article tags
        tag_elements = soup.select('.tag, .tags a, .post-tags a, [rel="tag"]')
        for element in tag_elements:
            tag = element.get_text().strip()
            if tag and tag not in tags:
                tags.append(tag)
        
        return tags
    
    def _extract_categories(self, soup: BeautifulSoup) -> List[str]:
        """Extract categories.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            List of categories
        """
        categories = []
        
        category_selectors = [
            '.category',
            '.categories a',
            '.post-category',
            '[rel="category"]',
        ]
        
        for selector in category_selectors:
            elements = soup.select(selector)
            for element in elements:
                category = element.get_text().strip()
                if category and category not in categories:
                    categories.append(category)
        
        return categories
    
    def _extract_breadcrumbs(self, soup: BeautifulSoup) -> List[str]:
        """Extract breadcrumb navigation.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            List of breadcrumb items
        """
        breadcrumbs = []
        
        # Try different breadcrumb selectors
        breadcrumb_selectors = [
            '.breadcrumb a',
            '.breadcrumbs a',
            '[aria-label="breadcrumb"] a',
            'nav[aria-label="Breadcrumb"] a',
        ]
        
        for selector in breadcrumb_selectors:
            elements = soup.select(selector)
            if elements:
                breadcrumbs = [elem.get_text().strip() for elem in elements]
                break
        
        return breadcrumbs
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract headings structure.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            List of heading dictionaries
        """
        headings = []
        
        for level in range(1, 7):  # h1 to h6
            for heading in soup.find_all(f'h{level}'):
                text = heading.get_text().strip()
                if text:
                    headings.append({
                        'level': level,
                        'text': text,
                        'id': heading.get('id', ''),
                    })
        
        return headings
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract links from content.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
        
        Returns:
            List of link dictionaries
        """
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            text = link.get_text().strip()
            
            if href and not href.startswith(('#', 'javascript:', 'mailto:')):
                absolute_url = urljoin(base_url, href)
                links.append({
                    'url': absolute_url,
                    'text': text,
                    'title': link.get('title', ''),
                })
        
        return links
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract images from content.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative URLs
        
        Returns:
            List of image dictionaries
        """
        images = []
        
        for img in soup.find_all('img', src=True):
            src = img.get('src')
            if src:
                absolute_url = urljoin(base_url, src)
                images.append({
                    'url': absolute_url,
                    'alt': img.get('alt', ''),
                    'title': img.get('title', ''),
                    'width': img.get('width', ''),
                    'height': img.get('height', ''),
                })
        
        return images
    
    def _extract_code_blocks(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract code blocks.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            List of code block dictionaries
        """
        code_blocks = []
        
        # Extract from pre/code elements
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                language = self._detect_code_language(code)
                code_blocks.append({
                    'language': language,
                    'code': code.get_text(),
                })
            else:
                code_blocks.append({
                    'language': 'text',
                    'code': pre.get_text(),
                })
        
        # Extract standalone code elements
        for code in soup.find_all('code'):
            if not code.find_parent('pre'):  # Skip if already in pre
                language = self._detect_code_language(code)
                code_blocks.append({
                    'language': language,
                    'code': code.get_text(),
                })
        
        return code_blocks
    
    def _detect_code_language(self, code_element: Tag) -> str:
        """Detect programming language of code block.
        
        Args:
            code_element: Code element
        
        Returns:
            Detected language or 'text'
        """
        # Check class attributes for language hints
        classes = code_element.get('class', [])
        for cls in classes:
            if cls.startswith('language-'):
                return cls[9:]  # Remove 'language-' prefix
            elif cls.startswith('lang-'):
                return cls[5:]  # Remove 'lang-' prefix
            elif cls in ['javascript', 'python', 'java', 'cpp', 'html', 'css', 'json', 'xml', 'sql']:
                return cls
        
        return 'text'
    
    def _extract_tables(self, soup: BeautifulSoup) -> List[str]:
        """Extract tables as text.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            List of table text representations
        """
        tables = []
        
        for table in soup.find_all('table'):
            table_text = self._table_to_text(table)
            if table_text:
                tables.append(table_text)
        
        return tables
    
    def _table_to_text(self, table: Tag) -> str:
        """Convert table to text representation.
        
        Args:
            table: Table element
        
        Returns:
            Text representation of table
        """
        rows = []
        
        for row in table.find_all('tr'):
            cells = []
            for cell in row.find_all(['td', 'th']):
                cell_text = cell.get_text().strip()
                cells.append(cell_text)
            
            if cells:
                rows.append(' | '.join(cells))
        
        return '\n'.join(rows)
    
    def _extract_lists(self, soup: BeautifulSoup) -> List[str]:
        """Extract lists as text.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            List of list text representations
        """
        lists = []
        
        for list_elem in soup.find_all(['ul', 'ol']):
            list_text = self._list_to_text(list_elem)
            if list_text:
                lists.append(list_text)
        
        return lists
    
    def _list_to_text(self, list_elem: Tag) -> str:
        """Convert list to text representation.
        
        Args:
            list_elem: List element
        
        Returns:
            Text representation of list
        """
        items = []
        
        for item in list_elem.find_all('li', recursive=False):
            item_text = item.get_text().strip()
            if item_text:
                prefix = '- ' if list_elem.name == 'ul' else f'{len(items) + 1}. '
                items.append(prefix + item_text)
        
        return '\n'.join(items)
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract additional metadata.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            Metadata dictionary
        """
        metadata = {}
        
        # Extract all meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property') or meta.get('http-equiv')
            content = meta.get('content')
            
            if name and content:
                metadata[name] = content
        
        # Extract structured data (JSON-LD)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json
                structured_data = json.loads(script.string)
                metadata['structured_data'] = structured_data
            except (json.JSONDecodeError, TypeError):
                pass
        
        return metadata
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text.
        
        Args:
            text: Raw text to clean
        
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate hash of content.
        
        Args:
            content: Content to hash
        
        Returns:
            Content hash
        """
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]