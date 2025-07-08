#!/usr/bin/env python3
"""
n8n Documentation Scraper

A comprehensive web scraper to extract all content from https://docs.n8n.io/
for building a complete knowledge base about n8n workflow automation.
"""

import requests
import time
import json
import os
import re
import hashlib
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup
from collections import deque
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Set, List, Dict, Optional
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/n8n_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class PageData:
    """Data structure for scraped page information"""
    url: str
    title: str
    content: str
    content_html: str  # New field for HTML content
    headings: List[str]
    links: List[str]
    code_blocks: List[str]
    images: List[str]
    metadata: Dict[str, str]
    scraped_at: str
    word_count: int
    content_hash: str

class N8nDocsScraper:
    """Scraper for n8n documentation with enhanced content extraction"""
    
    def __init__(self, base_url: str = "https://docs.n8n.io", max_pages: int = None, delay: float = 1.0, data_dir: str = "data", skip_existing: bool = True):
        self.base_url = base_url
        self.max_pages = max_pages
        self.delay = delay
        self.skip_existing = skip_existing
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'n8n-docs-scraper/1.0'})
        self.visited_urls = set()
        self.scraped_data = []
        self.data_dir = data_dir
        self.to_visit = deque([base_url])  # Initialize the queue with the base URL
        self.pages_skipped = 0
        self.errors = 0
        
        # Set up logging
        os.makedirs(f"{data_dir}/logs", exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{data_dir}/logs/n8n_scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Create output directory - changed from n8n_docs_data to scraped_docs
        self.output_dir = f"{data_dir}/scraped_docs"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def is_valid_url(self, url: str) -> bool:
        """Check if URL should be scraped"""
        parsed = urlparse(url)
        
        # Only scrape docs.n8n.io domain
        if parsed.netloc != 'docs.n8n.io':
            return False
            
        # Skip certain file types
        skip_extensions = {'.pdf', '.zip', '.tar', '.gz', '.exe', '.dmg'}
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False
            
        # Skip external links and anchors
        if url.startswith('#') or url.startswith('mailto:'):
            return False
            
        return True
    
    def extract_content(self, soup: BeautifulSoup, url: str) -> PageData:
        """Extract structured content from a page"""
        # Get page title
        title_elem = soup.find('title')
        title = title_elem.get_text().strip() if title_elem else "No Title"
        
        # Extract main content (try different selectors in order of preference)
        content_selectors = [
            'article',
            '.markdown-body',
            '.content',
            '.documentation',
            'main .content',
            'main',
            '.page-content'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.find('body')
        
        # Extract content with HTML formatting preserved
        content_text = ""
        content_html = ""
        if main_content:
            # Create a copy to avoid modifying the original
            content_copy = BeautifulSoup(str(main_content), 'html.parser')
            
            # Remove unwanted elements more aggressively
            unwanted_selectors = [
                'script', 'style', 'nav', 'header', 'footer',
                '.sidebar', '.navigation', '.nav', '.menu',
                '.breadcrumb', '.breadcrumbs', '.toc', '.table-of-contents',
                '.edit-page', '.edit-link', '.github-link',
                '.prev-next', '.pagination', '.page-nav',
                '.search', '.search-box', '.search-form',
                '.banner', '.alert', '.notice', '.warning',
                '.feedback', '.rating', '.social-share',
                '.related-links', '.see-also', '.external-links',
                '[role="navigation"]', '[role="banner"]', '[role="complementary"]',
                '.hidden', '.sr-only', '.visually-hidden'
            ]
            
            for selector in unwanted_selectors:
                for element in content_copy.select(selector):
                    element.decompose()
            
            # Remove elements with specific classes that indicate navigation/UI
            for element in content_copy.find_all(class_=True):
                classes = ' '.join(element.get('class', []))
                if any(keyword in classes.lower() for keyword in ['nav', 'menu', 'sidebar', 'header', 'footer', 'breadcrumb']):
                    element.decompose()
            
            # Clean up attributes to reduce HTML size
            for element in content_copy.find_all():
                # Keep only essential attributes
                attrs_to_keep = ['href', 'src', 'alt', 'title', 'id']
                if element.name in ['code', 'pre']:
                    attrs_to_keep.extend(['class', 'data-language'])
                if element.name in ['img']:
                    attrs_to_keep.extend(['width', 'height'])
                
                # Remove all other attributes
                attrs = dict(element.attrs)
                for attr in attrs:
                    if attr not in attrs_to_keep:
                        del element.attrs[attr]
            
            # Get cleaned HTML content
            content_html = str(content_copy)
            
            # Also extract plain text for search and word count
            content_text = content_copy.get_text(separator='\n', strip=True)
        else:
            # Fallback to full body content
            content_html = str(soup.find('body') or soup)
            content_text = soup.get_text(separator='\n', strip=True)
        
        # Extract headings
        headings = []
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                headings.append({
                    'level': i,
                    'text': heading.get_text().strip(),
                    'id': heading.get('id', '')
                })
        
        # Extract links
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(url, href)
            if self.is_valid_url(absolute_url):
                links.append({
                    'url': absolute_url,
                    'text': link.get_text().strip(),
                    'title': link.get('title', '')
                })
        
        # Extract code blocks
        code_blocks = []
        for code in soup.find_all(['code', 'pre']):
            code_text = code.get_text().strip()
            if code_text:
                code_blocks.append({
                    'content': code_text,
                    'language': code.get('class', [''])[0] if code.get('class') else '',
                    'type': code.name
                })
        
        # Extract images
        images = []
        for img in soup.find_all('img', src=True):
            images.append({
                'src': urljoin(url, img['src']),
                'alt': img.get('alt', ''),
                'title': img.get('title', '')
            })
        
        # Extract metadata
        metadata = {}
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                metadata[name] = content
        
        # Generate content hash for change detection
        content_hash = hashlib.md5(content_text.encode('utf-8')).hexdigest()
        
        return PageData(
            url=url,
            title=title,
            content=content_text,
            content_html=content_html,
            headings=headings,
            links=links,
            code_blocks=code_blocks,
            images=images,
            metadata=metadata,
            scraped_at=datetime.now().isoformat(),
            word_count=len(content_text.split()),
            content_hash=content_hash
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, requests.Timeout))
    )
    def scrape_page(self, url: str) -> Optional[PageData]:
        """Scrape a single page with retry logic"""
        try:
            logger.info(f"Scraping: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_data = self.extract_content(soup, url)
            
            # Add new URLs to visit queue
            for link_data in page_data.links:
                link_url = link_data['url']
                if link_url not in self.visited_urls and link_url not in self.to_visit:
                    self.to_visit.append(link_url)
            
            return page_data
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            self.errors += 1
            return None
    
    def _file_exists_and_current(self, filepath: Path, content_hash: str) -> bool:
        """Check if file exists and content hasn't changed"""
        if not filepath.exists():
            return False
            
        if not self.skip_existing:
            return False
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                return existing_data.get('content_hash') == content_hash
        except (json.JSONDecodeError, KeyError, IOError):
            return False
    
    def save_data(self, page_data: PageData) -> bool:
        """Save page data to JSON file with existence checking"""
        # Create filename from URL
        parsed_url = urlparse(page_data.url)
        filename = parsed_url.path.replace('/', '_').strip('_')
        if not filename:
            filename = 'index'
        filename = f"{filename}.json"
        
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        filepath = Path(self.output_dir) / filename
        
        # Handle duplicate filenames
        counter = 1
        original_filepath = filepath
        while filepath.exists() and not self._file_exists_and_current(filepath, page_data.content_hash):
            name = original_filepath.stem
            ext = original_filepath.suffix
            filepath = original_filepath.parent / f"{name}_{counter}{ext}"
            counter += 1
        
        # Skip if file exists and content hasn't changed
        if self._file_exists_and_current(filepath, page_data.content_hash):
            logger.info(f"Skipping existing file: {filepath}")
            self.pages_skipped += 1
            return False
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(page_data), f, indent=2, ensure_ascii=False)
            logger.info(f"Saved data to: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving data for {page_data.url}: {str(e)}")
            self.errors += 1
            return False
    
    def run(self, max_pages: Optional[int] = None):
        """Run the enhanced scraper"""
        logger.info(f"Starting enhanced scrape of {self.base_url}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Skip existing files: {self.skip_existing}")
        
        pages_scraped = 0
        start_time = datetime.now()
        
        while self.to_visit and (max_pages is None or pages_scraped < max_pages):
            url = self.to_visit.popleft()
            
            if url in self.visited_urls:
                continue
                
            self.visited_urls.add(url)
            
            page_data = self.scrape_page(url)
            if page_data:
                self.scraped_data.append(page_data)
                if self.save_data(page_data):
                    pages_scraped += 1
                
                # Log progress every 10 pages
                if (pages_scraped + self.pages_skipped) % 10 == 0:
                    elapsed = datetime.now() - start_time
                    rate = pages_scraped / max(elapsed.total_seconds() / 60, 1)
                    logger.info(f"Progress: {pages_scraped} scraped, {self.pages_skipped} skipped, "
                               f"{self.errors} errors, {len(self.to_visit)} in queue, "
                               f"{rate:.1f} pages/min")
            
            # Be respectful with delays
            time.sleep(self.delay)
        
        # Save summary
        self.save_summary()
        elapsed = datetime.now() - start_time
        logger.info(f"Scraping completed. Pages: {pages_scraped} scraped, {self.pages_skipped} skipped, "
                   f"{self.errors} errors. Time: {elapsed}")
    
    def save_summary(self):
        """Save enhanced scraping summary"""
        summary = {
            'scrape_config': {
                'base_url': self.base_url,
                'skip_existing': self.skip_existing,
                'delay': self.delay,
                'max_pages': self.max_pages
            },
            'statistics': {
                'total_pages_scraped': len(self.scraped_data),
                'pages_skipped': self.pages_skipped,
                'errors': self.errors,
                'total_words': sum(page.word_count for page in self.scraped_data)
            },
            'scrape_date': datetime.now().isoformat(),
            'pages': [
                {
                    'url': page.url,
                    'title': page.title,
                    'word_count': page.word_count,
                    'headings_count': len(page.headings),
                    'links_count': len(page.links),
                    'code_blocks_count': len(page.code_blocks),
                    'content_hash': page.content_hash
                }
                for page in self.scraped_data
            ]
        }
        
        summary_path = os.path.join(self.output_dir, 'scraping_summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Enhanced summary saved to: {summary_path}")

def main():
    """Main function to run the enhanced scraper"""
    scraper = N8nDocsScraper(
        base_url="https://docs.n8n.io/",
        delay=1.0,  # 1 second delay between requests
        skip_existing=True  # Skip files that already exist and haven't changed
    )
    
    # Run scraper (remove max_pages limit to scrape everything)
    scraper.run(max_pages=None)  # Set to None for unlimited scraping

if __name__ == "__main__":
    main()