"""URL management and pattern matching for web scraping."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Pattern, Any, Tuple
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
from urllib.robotparser import RobotFileParser

from ..core.exceptions import ValidationError, ScrapingError
from ..core.logging_config import get_logger
from ..core.metrics import metrics

logger = get_logger(__name__)


class URLType(Enum):
    """Type of URL content."""
    DOCUMENTATION = "documentation"
    API_REFERENCE = "api_reference"
    TUTORIAL = "tutorial"
    EXAMPLE = "example"
    CHANGELOG = "changelog"
    BLOG = "blog"
    FORUM = "forum"
    DOWNLOAD = "download"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class Priority(Enum):
    """URL scraping priority."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    SKIP = 5


@dataclass
class URLPattern:
    """URL pattern configuration."""
    pattern: str
    url_type: URLType = URLType.UNKNOWN
    priority: Priority = Priority.MEDIUM
    include: bool = True
    max_depth: Optional[int] = None
    follow_links: bool = True
    extract_content: bool = True
    custom_headers: Dict[str, str] = field(default_factory=dict)
    rate_limit_override: Optional[float] = None
    description: str = ""
    
    def __post_init__(self):
        """Compile regex pattern."""
        try:
            self.compiled_pattern: Pattern[str] = re.compile(self.pattern)
        except re.error as e:
            raise ValidationError(f"Invalid regex pattern '{self.pattern}': {e}")
    
    def matches(self, url: str) -> bool:
        """Check if URL matches this pattern.
        
        Args:
            url: URL to check
        
        Returns:
            True if URL matches pattern
        """
        return bool(self.compiled_pattern.search(url))


@dataclass
class URLInfo:
    """Information about a URL."""
    url: str
    url_type: URLType = URLType.UNKNOWN
    priority: Priority = Priority.MEDIUM
    depth: int = 0
    parent_url: Optional[str] = None
    discovered_at: Optional[str] = None
    last_scraped: Optional[str] = None
    scrape_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    content_hash: Optional[str] = None
    content_length: int = 0
    response_time: float = 0.0
    status_code: Optional[int] = None
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Normalize URL."""
        self.url = URLManager.normalize_url(self.url)


class RobotsChecker:
    """Robots.txt checker."""
    
    def __init__(self):
        """Initialize robots checker."""
        self._robots_cache: Dict[str, RobotFileParser] = {}
        self._user_agent = "n8n-scraper"
    
    def _get_robots_url(self, url: str) -> str:
        """Get robots.txt URL for a given URL.
        
        Args:
            url: URL to get robots.txt for
        
        Returns:
            Robots.txt URL
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    async def can_fetch(self, url: str, user_agent: Optional[str] = None) -> bool:
        """Check if URL can be fetched according to robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent to check for
        
        Returns:
            True if URL can be fetched
        """
        try:
            user_agent = user_agent or self._user_agent
            robots_url = self._get_robots_url(url)
            
            # Check cache
            if robots_url not in self._robots_cache:
                rp = RobotFileParser()
                rp.set_url(robots_url)
                try:
                    rp.read()
                    self._robots_cache[robots_url] = rp
                except Exception as e:
                    logger.debug(f"Failed to read robots.txt from {robots_url}: {e}")
                    # If robots.txt can't be read, assume allowed
                    return True
            
            rp = self._robots_cache[robots_url]
            return rp.can_fetch(user_agent, url)
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            # If there's an error, assume allowed
            return True
    
    def get_crawl_delay(self, url: str, user_agent: Optional[str] = None) -> Optional[float]:
        """Get crawl delay from robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent to check for
        
        Returns:
            Crawl delay in seconds, or None if not specified
        """
        try:
            user_agent = user_agent or self._user_agent
            robots_url = self._get_robots_url(url)
            
            if robots_url in self._robots_cache:
                rp = self._robots_cache[robots_url]
                return rp.crawl_delay(user_agent)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting crawl delay for {url}: {e}")
            return None


class URLManager:
    """Manages URLs for web scraping."""
    
    def __init__(self):
        """Initialize URL manager."""
        self.patterns: List[URLPattern] = []
        self.urls: Dict[str, URLInfo] = {}
        self.robots_checker = RobotsChecker()
        self._url_queue: List[URLInfo] = []
        self._processed_urls: Set[str] = set()
        self._blocked_domains: Set[str] = set()
        
        # Default patterns for n8n documentation
        self._setup_default_patterns()
    
    def _setup_default_patterns(self) -> None:
        """Setup default URL patterns for n8n."""
        default_patterns = [
            # Main documentation
            URLPattern(
                pattern=r"https://docs\.n8n\.io/.*",
                url_type=URLType.DOCUMENTATION,
                priority=Priority.HIGH,
                description="Main n8n documentation"
            ),
            
            # API reference
            URLPattern(
                pattern=r"https://docs\.n8n\.io/api/.*",
                url_type=URLType.API_REFERENCE,
                priority=Priority.CRITICAL,
                description="n8n API reference"
            ),
            
            # Tutorials
            URLPattern(
                pattern=r"https://docs\.n8n\.io/tutorials/.*",
                url_type=URLType.TUTORIAL,
                priority=Priority.HIGH,
                description="n8n tutorials"
            ),
            
            # Examples
            URLPattern(
                pattern=r"https://docs\.n8n\.io/examples/.*",
                url_type=URLType.EXAMPLE,
                priority=Priority.HIGH,
                description="n8n examples"
            ),
            
            # Changelog
            URLPattern(
                pattern=r"https://docs\.n8n\.io/changelog.*",
                url_type=URLType.CHANGELOG,
                priority=Priority.MEDIUM,
                description="n8n changelog"
            ),
            
            # Blog posts
            URLPattern(
                pattern=r"https://blog\.n8n\.io/.*",
                url_type=URLType.BLOG,
                priority=Priority.LOW,
                description="n8n blog"
            ),
            
            # Community forum
            URLPattern(
                pattern=r"https://community\.n8n\.io/.*",
                url_type=URLType.FORUM,
                priority=Priority.LOW,
                follow_links=False,
                description="n8n community forum"
            ),
            
            # External links (lower priority)
            URLPattern(
                pattern=r"https?://(?!.*\.n8n\.io).*",
                url_type=URLType.EXTERNAL,
                priority=Priority.SKIP,
                include=False,
                description="External links"
            ),
        ]
        
        for pattern in default_patterns:
            self.add_pattern(pattern)
    
    def add_pattern(self, pattern: URLPattern) -> None:
        """Add a URL pattern.
        
        Args:
            pattern: URL pattern to add
        """
        self.patterns.append(pattern)
        logger.debug(f"Added URL pattern: {pattern.pattern} ({pattern.url_type.value})")
    
    def remove_pattern(self, pattern_str: str) -> bool:
        """Remove a URL pattern.
        
        Args:
            pattern_str: Pattern string to remove
        
        Returns:
            True if pattern was removed
        """
        for i, pattern in enumerate(self.patterns):
            if pattern.pattern == pattern_str:
                del self.patterns[i]
                logger.debug(f"Removed URL pattern: {pattern_str}")
                return True
        return False
    
    def classify_url(self, url: str) -> Tuple[URLType, Priority, URLPattern]:
        """Classify a URL based on patterns.
        
        Args:
            url: URL to classify
        
        Returns:
            Tuple of (url_type, priority, matching_pattern)
        """
        for pattern in self.patterns:
            if pattern.matches(url):
                return pattern.url_type, pattern.priority, pattern
        
        # Default classification
        default_pattern = URLPattern(
            pattern=".*",
            url_type=URLType.UNKNOWN,
            priority=Priority.MEDIUM
        )
        return URLType.UNKNOWN, Priority.MEDIUM, default_pattern
    
    def should_scrape_url(self, url: str, respect_robots: bool = True) -> Tuple[bool, str]:
        """Check if URL should be scraped.
        
        Args:
            url: URL to check
            respect_robots: Whether to respect robots.txt
        
        Returns:
            Tuple of (should_scrape, reason)
        """
        # Check if already processed
        if url in self._processed_urls:
            return False, "Already processed"
        
        # Check domain blocking
        domain = self.get_domain(url)
        if domain in self._blocked_domains:
            return False, f"Domain blocked: {domain}"
        
        # Classify URL
        url_type, priority, pattern = self.classify_url(url)
        
        # Check if pattern allows scraping
        if not pattern.include or priority == Priority.SKIP:
            return False, f"Pattern excludes URL: {pattern.pattern}"
        
        # Check robots.txt if enabled
        if respect_robots:
            # This would need to be async in real usage
            # For now, we'll assume it's allowed
            pass
        
        return True, "URL allowed for scraping"
    
    def add_url(self, url: str, parent_url: Optional[str] = None, depth: int = 0) -> URLInfo:
        """Add a URL to be managed.
        
        Args:
            url: URL to add
            parent_url: Parent URL that discovered this URL
            depth: Depth level of the URL
        
        Returns:
            URLInfo object
        """
        normalized_url = self.normalize_url(url)
        
        if normalized_url in self.urls:
            return self.urls[normalized_url]
        
        # Classify URL
        url_type, priority, pattern = self.classify_url(normalized_url)
        
        url_info = URLInfo(
            url=normalized_url,
            url_type=url_type,
            priority=priority,
            depth=depth,
            parent_url=parent_url
        )
        
        self.urls[normalized_url] = url_info
        
        # Add to queue if should be scraped
        should_scrape, reason = self.should_scrape_url(normalized_url)
        if should_scrape:
            self._url_queue.append(url_info)
            self._url_queue.sort(key=lambda x: x.priority.value)
        
        logger.debug(f"Added URL: {normalized_url} (type: {url_type.value}, priority: {priority.value})")
        metrics.increment_counter("url_manager_urls_added")
        
        return url_info
    
    def get_next_url(self) -> Optional[URLInfo]:
        """Get the next URL to scrape.
        
        Returns:
            Next URL to scrape, or None if queue is empty
        """
        while self._url_queue:
            url_info = self._url_queue.pop(0)
            
            # Double-check if URL should still be scraped
            should_scrape, reason = self.should_scrape_url(url_info.url)
            if should_scrape:
                return url_info
            else:
                logger.debug(f"Skipping URL {url_info.url}: {reason}")
        
        return None
    
    def mark_url_processed(self, url: str) -> None:
        """Mark URL as processed.
        
        Args:
            url: URL to mark as processed
        """
        normalized_url = self.normalize_url(url)
        self._processed_urls.add(normalized_url)
        
        if normalized_url in self.urls:
            self.urls[normalized_url].scrape_count += 1
        
        metrics.increment_counter("url_manager_urls_processed")
    
    def mark_url_error(self, url: str, error: str) -> None:
        """Mark URL as having an error.
        
        Args:
            url: URL that had an error
            error: Error message
        """
        normalized_url = self.normalize_url(url)
        
        if normalized_url in self.urls:
            url_info = self.urls[normalized_url]
            url_info.error_count += 1
            url_info.last_error = error
        
        metrics.increment_counter("url_manager_url_errors")
    
    def block_domain(self, domain: str) -> None:
        """Block a domain from being scraped.
        
        Args:
            domain: Domain to block
        """
        self._blocked_domains.add(domain.lower())
        logger.info(f"Blocked domain: {domain}")
    
    def unblock_domain(self, domain: str) -> None:
        """Unblock a domain.
        
        Args:
            domain: Domain to unblock
        """
        self._blocked_domains.discard(domain.lower())
        logger.info(f"Unblocked domain: {domain}")
    
    def get_queue_size(self) -> int:
        """Get the size of the URL queue.
        
        Returns:
            Number of URLs in queue
        """
        return len(self._url_queue)
    
    def get_processed_count(self) -> int:
        """Get the number of processed URLs.
        
        Returns:
            Number of processed URLs
        """
        return len(self._processed_urls)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get URL manager statistics.
        
        Returns:
            Statistics dictionary
        """
        url_types = {}
        priorities = {}
        
        for url_info in self.urls.values():
            url_type = url_info.url_type.value
            priority = url_info.priority.value
            
            url_types[url_type] = url_types.get(url_type, 0) + 1
            priorities[priority] = priorities.get(priority, 0) + 1
        
        return {
            "total_urls": len(self.urls),
            "queued_urls": len(self._url_queue),
            "processed_urls": len(self._processed_urls),
            "blocked_domains": len(self._blocked_domains),
            "patterns_count": len(self.patterns),
            "url_types": url_types,
            "priorities": priorities,
            "error_urls": sum(1 for url in self.urls.values() if url.error_count > 0),
        }
    
    def clear_queue(self) -> None:
        """Clear the URL queue."""
        self._url_queue.clear()
        logger.info("Cleared URL queue")
    
    def reset_processed(self) -> None:
        """Reset processed URLs tracking."""
        self._processed_urls.clear()
        for url_info in self.urls.values():
            url_info.scrape_count = 0
            url_info.error_count = 0
            url_info.last_error = None
        logger.info("Reset processed URLs tracking")
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize a URL.
        
        Args:
            url: URL to normalize
        
        Returns:
            Normalized URL
        """
        try:
            # Parse URL
            parsed = urlparse(url.strip())
            
            # Normalize scheme
            scheme = parsed.scheme.lower() if parsed.scheme else 'https'
            
            # Normalize netloc
            netloc = parsed.netloc.lower()
            
            # Normalize path
            path = parsed.path
            if not path:
                path = '/'
            
            # Remove default ports
            if ':80' in netloc and scheme == 'http':
                netloc = netloc.replace(':80', '')
            elif ':443' in netloc and scheme == 'https':
                netloc = netloc.replace(':443', '')
            
            # Normalize query parameters
            query = parsed.query
            if query:
                # Sort query parameters for consistency
                params = parse_qs(query, keep_blank_values=True)
                sorted_params = sorted(params.items())
                query = urlencode(sorted_params, doseq=True)
            
            # Reconstruct URL
            normalized = urlunparse((
                scheme,
                netloc,
                path,
                parsed.params,
                query,
                ''  # Remove fragment
            ))
            
            return normalized
            
        except Exception as e:
            logger.warning(f"Failed to normalize URL '{url}': {e}")
            return url
    
    @staticmethod
    def get_domain(url: str) -> str:
        """Extract domain from URL.
        
        Args:
            url: URL to extract domain from
        
        Returns:
            Domain name
        """
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return "unknown"
    
    @staticmethod
    def is_same_domain(url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain.
        
        Args:
            url1: First URL
            url2: Second URL
        
        Returns:
            True if URLs are from the same domain
        """
        return URLManager.get_domain(url1) == URLManager.get_domain(url2)
    
    @staticmethod
    def resolve_relative_url(base_url: str, relative_url: str) -> str:
        """Resolve a relative URL against a base URL.
        
        Args:
            base_url: Base URL
            relative_url: Relative URL
        
        Returns:
            Absolute URL
        """
        try:
            return urljoin(base_url, relative_url)
        except Exception as e:
            logger.warning(f"Failed to resolve relative URL '{relative_url}' against '{base_url}': {e}")
            return relative_url
    
    def extract_urls_from_content(self, content: str, base_url: str) -> List[str]:
        """Extract URLs from HTML content.
        
        Args:
            content: HTML content
            base_url: Base URL for resolving relative URLs
        
        Returns:
            List of extracted URLs
        """
        urls = []
        
        # Simple regex-based URL extraction
        # In a real implementation, you'd use BeautifulSoup or similar
        url_patterns = [
            r'href=["\']([^"\'>]+)["\']',
            r'src=["\']([^"\'>]+)["\']',
            r'action=["\']([^"\'>]+)["\']',
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if match and not match.startswith(('#', 'javascript:', 'mailto:')):
                    absolute_url = self.resolve_relative_url(base_url, match)
                    normalized_url = self.normalize_url(absolute_url)
                    urls.append(normalized_url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls