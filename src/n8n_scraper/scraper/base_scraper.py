"""
Base scraper class and interfaces.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Any, AsyncGenerator, Union
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from config.settings import settings
from ..core.exceptions import (
    ScrapingError,
    ScrapingTimeoutError,
    ScrapingRateLimitError,
    ValidationError
)
from ..core.logging_config import get_logger
from ..core.metrics import metrics, timing_decorator

logger = get_logger(__name__)


class ScrapingStatus(Enum):
    """Status of scraping operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RATE_LIMITED = "rate_limited"


class ContentType(Enum):
    """Type of scraped content."""
    DOCUMENTATION = "documentation"
    API_REFERENCE = "api_reference"
    TUTORIAL = "tutorial"
    EXAMPLE = "example"
    CHANGELOG = "changelog"
    FAQ = "faq"
    BLOG_POST = "blog_post"
    UNKNOWN = "unknown"


@dataclass
class ScrapingMetadata:
    """Metadata for scraped content."""
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    content_type: ContentType = ContentType.UNKNOWN
    language: str = "en"
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    section: Optional[str] = None
    breadcrumbs: List[str] = field(default_factory=list)
    word_count: int = 0
    reading_time_minutes: int = 0
    difficulty_level: Optional[str] = None
    prerequisites: List[str] = field(default_factory=list)
    related_urls: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    code_blocks: int = 0
    external_links: int = 0
    internal_links: int = 0


@dataclass
class ScrapingResult:
    """Result of a scraping operation."""
    url: str
    status: ScrapingStatus
    content: Optional[str] = None
    metadata: Optional[ScrapingMetadata] = None
    error: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    processing_time_seconds: float = 0.0
    response_status: Optional[int] = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    content_length: int = 0
    content_hash: Optional[str] = None
    quality_score: float = 0.0
    
    def is_successful(self) -> bool:
        """Check if scraping was successful."""
        return self.status == ScrapingStatus.COMPLETED and self.content is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "status": self.status.value,
            "content": self.content,
            "metadata": self.metadata.__dict__ if self.metadata else None,
            "error": self.error,
            "scraped_at": self.scraped_at.isoformat(),
            "processing_time_seconds": self.processing_time_seconds,
            "response_status": self.response_status,
            "response_headers": self.response_headers,
            "content_length": self.content_length,
            "content_hash": self.content_hash,
            "quality_score": self.quality_score,
        }


@dataclass
class ScrapingConfig:
    """Configuration for scraping operations."""
    max_concurrent_requests: int = 10
    request_timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    rate_limit_delay: float = 1.0
    user_agent: str = "n8n-scraper/1.0"
    follow_redirects: bool = True
    max_redirects: int = 5
    verify_ssl: bool = True
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    proxy: Optional[str] = None
    max_content_size: int = 10 * 1024 * 1024  # 10MB
    allowed_content_types: Set[str] = field(default_factory=lambda: {
        "text/html",
        "application/xhtml+xml",
        "text/plain"
    })
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    respect_robots_txt: bool = True
    crawl_delay: float = 1.0
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.max_concurrent_requests <= 0:
            raise ValidationError("max_concurrent_requests must be positive")
        if self.request_timeout <= 0:
            raise ValidationError("request_timeout must be positive")
        if self.retry_attempts < 0:
            raise ValidationError("retry_attempts must be non-negative")


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize the scraper.
        
        Args:
            config: Scraping configuration
        """
        self.config = config or ScrapingConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self._scraped_urls: Set[str] = set()
        self._failed_urls: Set[str] = set()
        self._semaphore: Optional[asyncio.Semaphore] = None
        
        # Setup default headers
        self.default_headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.default_headers.update(self.config.headers)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self) -> None:
        """Start the scraper session."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
            connector = aiohttp.TCPConnector(
                limit=self.config.max_concurrent_requests,
                verify_ssl=self.config.verify_ssl
            )
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=self.default_headers,
                cookies=self.config.cookies
            )
            
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
            
            logger.info(f"Started {self.__class__.__name__} with {self.config.max_concurrent_requests} concurrent requests")
    
    async def close(self) -> None:
        """Close the scraper session."""
        if self.session:
            await self.session.close()
            self.session = None
            self._semaphore = None
            
            logger.info(f"Closed {self.__class__.__name__}")
    
    @abstractmethod
    async def scrape_url(self, url: str) -> ScrapingResult:
        """Scrape a single URL.
        
        Args:
            url: URL to scrape
        
        Returns:
            Scraping result
        """
        pass
    
    @abstractmethod
    async def scrape_urls(self, urls: List[str]) -> AsyncGenerator[ScrapingResult, None]:
        """Scrape multiple URLs.
        
        Args:
            urls: List of URLs to scrape
        
        Yields:
            Scraping results
        """
        pass
    
    @abstractmethod
    def extract_content(self, html: str, url: str) -> tuple[str, ScrapingMetadata]:
        """Extract content and metadata from HTML.
        
        Args:
            html: Raw HTML content
            url: Source URL
        
        Returns:
            Tuple of (extracted_content, metadata)
        """
        pass
    
    @timing_decorator("scraper_fetch_url")
    async def fetch_url(self, url: str) -> tuple[str, Dict[str, str], int]:
        """Fetch content from a URL.
        
        Args:
            url: URL to fetch
        
        Returns:
            Tuple of (content, headers, status_code)
        
        Raises:
            ScrapingError: If fetching fails
            ScrapingTimeoutError: If request times out
            ScrapingRateLimitError: If rate limited
        """
        if not self.session:
            raise ScrapingError("Scraper session not started")
        
        if not self._semaphore:
            raise ScrapingError("Semaphore not initialized")
        
        async with self._semaphore:
            try:
                # Apply rate limiting
                await asyncio.sleep(self.config.rate_limit_delay)
                
                # Make request with retries
                for attempt in range(self.config.retry_attempts + 1):
                    try:
                        async with self.session.get(
                            url,
                            allow_redirects=self.config.follow_redirects,
                            max_redirects=self.config.max_redirects,
                            proxy=self.config.proxy
                        ) as response:
                            # Check content type
                            content_type = response.headers.get("content-type", "").lower()
                            if not any(ct in content_type for ct in self.config.allowed_content_types):
                                raise ScrapingError(f"Unsupported content type: {content_type}")
                            
                            # Check content size
                            content_length = response.headers.get("content-length")
                            if content_length and int(content_length) > self.config.max_content_size:
                                raise ScrapingError(f"Content too large: {content_length} bytes")
                            
                            # Handle rate limiting
                            if response.status == 429:
                                retry_after = response.headers.get("retry-after")
                                delay = float(retry_after) if retry_after else self.config.retry_delay * (2 ** attempt)
                                
                                if attempt < self.config.retry_attempts:
                                    logger.warning(f"Rate limited for {url}, retrying after {delay}s")
                                    await asyncio.sleep(delay)
                                    continue
                                else:
                                    raise ScrapingRateLimitError(f"Rate limited: {url}")
                            
                            # Raise for HTTP errors
                            response.raise_for_status()
                            
                            # Read content
                            content = await response.text()
                            
                            # Check actual content size
                            if len(content.encode('utf-8')) > self.config.max_content_size:
                                raise ScrapingError(f"Content too large after download: {len(content)} characters")
                            
                            headers = dict(response.headers)
                            status_code = response.status
                            
                            metrics.increment_counter("scraper_requests_successful")
                            return content, headers, status_code
                    
                    except asyncio.TimeoutError:
                        if attempt < self.config.retry_attempts:
                            logger.warning(f"Timeout for {url}, retrying (attempt {attempt + 1})")
                            await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                            continue
                        else:
                            metrics.increment_counter("scraper_requests_timeout")
                            raise ScrapingTimeoutError(f"Request timeout: {url}")
                    
                    except aiohttp.ClientError as e:
                        if attempt < self.config.retry_attempts:
                            logger.warning(f"Client error for {url}: {e}, retrying (attempt {attempt + 1})")
                            await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                            continue
                        else:
                            metrics.increment_counter("scraper_requests_failed")
                            raise ScrapingError(f"Client error: {url} - {str(e)}") from e
                
                # If we get here, all retries failed
                metrics.increment_counter("scraper_requests_failed")
                raise ScrapingError(f"All retry attempts failed for: {url}")
            
            except Exception as e:
                metrics.increment_counter("scraper_requests_error")
                if isinstance(e, (ScrapingError, ScrapingTimeoutError, ScrapingRateLimitError)):
                    raise
                else:
                    raise ScrapingError(f"Unexpected error fetching {url}: {str(e)}") from e
    
    def should_scrape_url(self, url: str) -> bool:
        """Check if URL should be scraped.
        
        Args:
            url: URL to check
        
        Returns:
            True if URL should be scraped
        """
        # Check if already scraped
        if url in self._scraped_urls:
            return False
        
        # Check if previously failed
        if url in self._failed_urls:
            return False
        
        # Check include patterns
        if self.config.include_patterns:
            if not any(pattern in url for pattern in self.config.include_patterns):
                return False
        
        # Check exclude patterns
        if self.config.exclude_patterns:
            if any(pattern in url for pattern in self.config.exclude_patterns):
                return False
        
        return True
    
    def mark_url_scraped(self, url: str) -> None:
        """Mark URL as scraped.
        
        Args:
            url: URL to mark as scraped
        """
        self._scraped_urls.add(url)
    
    def mark_url_failed(self, url: str) -> None:
        """Mark URL as failed.
        
        Args:
            url: URL to mark as failed
        """
        self._failed_urls.add(url)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "scraped_urls": len(self._scraped_urls),
            "failed_urls": len(self._failed_urls),
            "total_processed": len(self._scraped_urls) + len(self._failed_urls),
            "success_rate": len(self._scraped_urls) / max(1, len(self._scraped_urls) + len(self._failed_urls)),
            "config": {
                "max_concurrent_requests": self.config.max_concurrent_requests,
                "request_timeout": self.config.request_timeout,
                "retry_attempts": self.config.retry_attempts,
                "rate_limit_delay": self.config.rate_limit_delay,
            }
        }
    
    def reset_stats(self) -> None:
        """Reset scraping statistics."""
        self._scraped_urls.clear()
        self._failed_urls.clear()
    
    @staticmethod
    def normalize_url(url: str, base_url: Optional[str] = None) -> str:
        """Normalize URL.
        
        Args:
            url: URL to normalize
            base_url: Base URL for relative URLs
        
        Returns:
            Normalized URL
        """
        if base_url and not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)
        
        # Remove fragment
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}{parsed.params and ';' + parsed.params or ''}{parsed.query and '?' + parsed.query or ''}"
    
    @staticmethod
    def extract_links(html: str, base_url: str) -> List[str]:
        """Extract links from HTML.
        
        Args:
            html: HTML content
            base_url: Base URL for relative links
        
        Returns:
            List of normalized URLs
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href and not href.startswith(('#', 'javascript:', 'mailto:')):
                normalized_url = BaseScraper.normalize_url(href, base_url)
                links.append(normalized_url)
        
        return list(set(links))  # Remove duplicates