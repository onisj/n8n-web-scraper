"""
Factory for creating and configuring scrapers.
"""

from typing import Dict, Type, Optional, Any, List
from dataclasses import dataclass, field
from enum import Enum

from ..core.exceptions import ConfigurationError
from ..core.logging_config import get_logger
from .base_scraper import BaseScraper, ScrapingConfig
from .rate_limiter import RateLimitConfig
from .session_manager import SessionConfig, ProxyConfig
from .url_manager import URLPattern
from .content_processor import ProcessingConfig

logger = get_logger(__name__)


class ScraperType(Enum):
    """Available scraper types."""
    N8N = "n8n"
    GENERIC = "generic"
    DOCUMENTATION = "documentation"
    BLOG = "blog"
    API_DOCS = "api_docs"


@dataclass
class ScraperFactoryConfig:
    """Configuration for scraper factory."""
    # Default configurations
    default_scraping_config: Optional[ScrapingConfig] = None
    default_rate_limit_config: Optional[RateLimitConfig] = None
    default_session_config: Optional[SessionConfig] = None
    default_processing_config: Optional[ProcessingConfig] = None
    
    # Scraper-specific overrides
    scraper_configs: Dict[ScraperType, Dict[str, Any]] = field(default_factory=dict)
    
    # URL patterns for different scraper types
    url_patterns: Dict[ScraperType, List[URLPattern]] = field(default_factory=dict)
    
    # Feature flags
    enable_caching: bool = True
    enable_metrics: bool = True
    enable_retry: bool = True


class ScraperFactory:
    """Factory for creating configured scrapers."""
    
    def __init__(self, config: Optional[ScraperFactoryConfig] = None):
        """Initialize scraper factory.
        
        Args:
            config: Factory configuration
        """
        self.config = config or ScraperFactoryConfig()
        self._scraper_registry: Dict[ScraperType, Type[BaseScraper]] = {}
        self._default_configs = self._setup_default_configs()
        self._setup_url_patterns()
        
        # Register built-in scrapers
        self._register_builtin_scrapers()
    
    def _setup_default_configs(self) -> Dict[str, Any]:
        """Setup default configurations.
        
        Returns:
            Default configurations dictionary
        """
        return {
            'scraping': self.config.default_scraping_config or ScrapingConfig(
                max_pages=1000,
                max_depth=5,
                delay_range=(1.0, 3.0),
                timeout=30.0,
                max_retries=3,
                respect_robots_txt=True,
                follow_redirects=True,
                max_file_size=10 * 1024 * 1024,  # 10MB
                allowed_content_types={'text/html', 'application/xhtml+xml'},
            ),
            'rate_limit': self.config.default_rate_limit_config or RateLimitConfig(
                requests_per_second=2.0,
                burst_size=5,
                window_size=60,
                max_requests_per_window=100,
                adaptive_delay=True,
                respect_retry_after=True,
            ),
            'session': self.config.default_session_config or SessionConfig(
                timeout=30.0,
                max_connections=100,
                max_connections_per_host=10,
                enable_compression=True,
                follow_redirects=True,
                max_redirects=10,
                verify_ssl=True,
                headers={
                    'User-Agent': 'n8n-scraper/1.0 (+https://n8n.io)',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
            ),
            'processing': self.config.default_processing_config or ProcessingConfig(
                min_quality_score=40.0,
                min_word_count=50,
                max_word_count=50000,
                enable_quality_check=True,
                enable_content_cleaning=True,
                enable_enrichment=True,
                enable_chunking=True,
                chunk_size=1000,
                chunk_overlap=200,
                max_chunks_per_document=100,
                max_concurrent_processes=5,
            ),
        }
    
    def _setup_url_patterns(self) -> None:
        """Setup URL patterns for different scraper types."""
        if not self.config.url_patterns:
            self.config.url_patterns = {
                ScraperType.N8N: self._get_n8n_url_patterns(),
                ScraperType.DOCUMENTATION: self._get_documentation_url_patterns(),
                ScraperType.BLOG: self._get_blog_url_patterns(),
                ScraperType.API_DOCS: self._get_api_docs_url_patterns(),
                ScraperType.GENERIC: self._get_generic_url_patterns(),
            }
    
    def _get_n8n_url_patterns(self) -> List[URLPattern]:
        """Get URL patterns for n8n documentation.
        
        Returns:
            List of URL patterns
        """
        from .url_manager import URLType, Priority
        
        return [
            URLPattern(
                pattern=r'https://docs\.n8n\.io/.*',
                url_type=URLType.DOCUMENTATION,
                priority=Priority.HIGH,
                should_scrape=True,
                follow_links=True,
                max_depth=5,
            ),
            URLPattern(
                pattern=r'https://docs\.n8n\.io/integrations/.*',
                url_type=URLType.INTEGRATION,
                priority=Priority.HIGH,
                should_scrape=True,
                follow_links=True,
                max_depth=3,
            ),
            URLPattern(
                pattern=r'https://docs\.n8n\.io/code/.*',
                url_type=URLType.CODE_EXAMPLE,
                priority=Priority.HIGH,
                should_scrape=True,
                follow_links=True,
                max_depth=4,
            ),
            URLPattern(
                pattern=r'https://docs\.n8n\.io/api/.*',
                url_type=URLType.API_REFERENCE,
                priority=Priority.MEDIUM,
                should_scrape=True,
                follow_links=True,
                max_depth=3,
            ),
            URLPattern(
                pattern=r'https://blog\.n8n\.io/.*',
                url_type=URLType.BLOG_POST,
                priority=Priority.MEDIUM,
                should_scrape=True,
                follow_links=False,
                max_depth=1,
            ),
            URLPattern(
                pattern=r'https://community\.n8n\.io/.*',
                url_type=URLType.FORUM_POST,
                priority=Priority.LOW,
                should_scrape=False,  # Community content might be too dynamic
                follow_links=False,
                max_depth=1,
            ),
        ]
    
    def _get_documentation_url_patterns(self) -> List[URLPattern]:
        """Get generic documentation URL patterns.
        
        Returns:
            List of URL patterns
        """
        from .url_manager import URLType, Priority
        
        return [
            URLPattern(
                pattern=r'.*/docs?/.*',
                url_type=URLType.DOCUMENTATION,
                priority=Priority.HIGH,
                should_scrape=True,
                follow_links=True,
                max_depth=4,
            ),
            URLPattern(
                pattern=r'.*/documentation/.*',
                url_type=URLType.DOCUMENTATION,
                priority=Priority.HIGH,
                should_scrape=True,
                follow_links=True,
                max_depth=4,
            ),
            URLPattern(
                pattern=r'.*/guide/.*',
                url_type=URLType.TUTORIAL,
                priority=Priority.HIGH,
                should_scrape=True,
                follow_links=True,
                max_depth=3,
            ),
        ]
    
    def _get_blog_url_patterns(self) -> List[URLPattern]:
        """Get blog URL patterns.
        
        Returns:
            List of URL patterns
        """
        from .url_manager import URLType, Priority
        
        return [
            URLPattern(
                pattern=r'.*/blog/.*',
                url_type=URLType.BLOG_POST,
                priority=Priority.MEDIUM,
                should_scrape=True,
                follow_links=False,
                max_depth=1,
            ),
            URLPattern(
                pattern=r'.*/post/.*',
                url_type=URLType.BLOG_POST,
                priority=Priority.MEDIUM,
                should_scrape=True,
                follow_links=False,
                max_depth=1,
            ),
            URLPattern(
                pattern=r'.*/article/.*',
                url_type=URLType.BLOG_POST,
                priority=Priority.MEDIUM,
                should_scrape=True,
                follow_links=False,
                max_depth=1,
            ),
        ]
    
    def _get_api_docs_url_patterns(self) -> List[URLPattern]:
        """Get API documentation URL patterns.
        
        Returns:
            List of URL patterns
        """
        from .url_manager import URLType, Priority
        
        return [
            URLPattern(
                pattern=r'.*/api/.*',
                url_type=URLType.API_REFERENCE,
                priority=Priority.HIGH,
                should_scrape=True,
                follow_links=True,
                max_depth=3,
            ),
            URLPattern(
                pattern=r'.*/reference/.*',
                url_type=URLType.API_REFERENCE,
                priority=Priority.HIGH,
                should_scrape=True,
                follow_links=True,
                max_depth=3,
            ),
        ]
    
    def _get_generic_url_patterns(self) -> List[URLPattern]:
        """Get generic URL patterns.
        
        Returns:
            List of URL patterns
        """
        from .url_manager import URLType, Priority
        
        return [
            URLPattern(
                pattern=r'.*',
                url_type=URLType.GENERAL,
                priority=Priority.LOW,
                should_scrape=True,
                follow_links=True,
                max_depth=2,
            ),
        ]
    
    def _register_builtin_scrapers(self) -> None:
        """Register built-in scraper types."""
        # Import here to avoid circular imports
        try:
            from .n8n_scraper import N8nScraper
            self.register_scraper(ScraperType.N8N, N8nScraper)
        except ImportError:
            logger.warning("N8nScraper not available")
        
        # Register generic scraper as fallback
        self.register_scraper(ScraperType.GENERIC, BaseScraper)
    
    def register_scraper(self, scraper_type: ScraperType, scraper_class: Type[BaseScraper]) -> None:
        """Register a scraper type.
        
        Args:
            scraper_type: Type of scraper
            scraper_class: Scraper class
        """
        self._scraper_registry[scraper_type] = scraper_class
        logger.info(f"Registered scraper type: {scraper_type.value}")
    
    def create_scraper(self, 
                      scraper_type: ScraperType,
                      **kwargs) -> BaseScraper:
        """Create a configured scraper.
        
        Args:
            scraper_type: Type of scraper to create
            **kwargs: Additional configuration overrides
        
        Returns:
            Configured scraper instance
        
        Raises:
            ConfigurationError: If scraper type is not registered
        """
        if scraper_type not in self._scraper_registry:
            raise ConfigurationError(f"Scraper type {scraper_type.value} not registered")
        
        scraper_class = self._scraper_registry[scraper_type]
        
        # Build configuration
        config = self._build_scraper_config(scraper_type, **kwargs)
        
        # Create scraper instance
        try:
            scraper = scraper_class(**config)
            logger.info(f"Created {scraper_type.value} scraper")
            return scraper
        except Exception as e:
            raise ConfigurationError(f"Failed to create {scraper_type.value} scraper: {str(e)}") from e
    
    def _build_scraper_config(self, scraper_type: ScraperType, **kwargs) -> Dict[str, Any]:
        """Build configuration for scraper.
        
        Args:
            scraper_type: Type of scraper
            **kwargs: Configuration overrides
        
        Returns:
            Configuration dictionary
        """
        config = {}
        
        # Start with default configurations
        for config_name, default_config in self._default_configs.items():
            config[f'{config_name}_config'] = default_config
        
        # Apply scraper-specific configurations
        if scraper_type in self.config.scraper_configs:
            scraper_specific = self.config.scraper_configs[scraper_type]
            for key, value in scraper_specific.items():
                if key.endswith('_config') and key in config:
                    # Merge configuration objects
                    if hasattr(config[key], '__dict__'):
                        for attr, attr_value in value.__dict__.items():
                            setattr(config[key], attr, attr_value)
                    else:
                        config[key] = value
                else:
                    config[key] = value
        
        # Apply URL patterns
        if scraper_type in self.config.url_patterns:
            config['url_patterns'] = self.config.url_patterns[scraper_type]
        
        # Apply runtime overrides
        for key, value in kwargs.items():
            config[key] = value
        
        return config
    
    def create_n8n_scraper(self, **kwargs) -> BaseScraper:
        """Create an n8n documentation scraper.
        
        Args:
            **kwargs: Configuration overrides
        
        Returns:
            Configured n8n scraper
        """
        return self.create_scraper(ScraperType.N8N, **kwargs)
    
    def create_documentation_scraper(self, **kwargs) -> BaseScraper:
        """Create a documentation scraper.
        
        Args:
            **kwargs: Configuration overrides
        
        Returns:
            Configured documentation scraper
        """
        return self.create_scraper(ScraperType.DOCUMENTATION, **kwargs)
    
    def create_blog_scraper(self, **kwargs) -> BaseScraper:
        """Create a blog scraper.
        
        Args:
            **kwargs: Configuration overrides
        
        Returns:
            Configured blog scraper
        """
        return self.create_scraper(ScraperType.BLOG, **kwargs)
    
    def create_api_docs_scraper(self, **kwargs) -> BaseScraper:
        """Create an API documentation scraper.
        
        Args:
            **kwargs: Configuration overrides
        
        Returns:
            Configured API docs scraper
        """
        return self.create_scraper(ScraperType.API_DOCS, **kwargs)
    
    def create_generic_scraper(self, **kwargs) -> BaseScraper:
        """Create a generic scraper.
        
        Args:
            **kwargs: Configuration overrides
        
        Returns:
            Configured generic scraper
        """
        return self.create_scraper(ScraperType.GENERIC, **kwargs)
    
    def get_available_scrapers(self) -> List[ScraperType]:
        """Get list of available scraper types.
        
        Returns:
            List of registered scraper types
        """
        return list(self._scraper_registry.keys())
    
    def configure_scraper_type(self, 
                              scraper_type: ScraperType, 
                              config: Dict[str, Any]) -> None:
        """Configure a specific scraper type.
        
        Args:
            scraper_type: Scraper type to configure
            config: Configuration dictionary
        """
        self.config.scraper_configs[scraper_type] = config
        logger.info(f"Configured scraper type: {scraper_type.value}")
    
    def add_url_patterns(self, 
                        scraper_type: ScraperType, 
                        patterns: List[URLPattern]) -> None:
        """Add URL patterns for a scraper type.
        
        Args:
            scraper_type: Scraper type
            patterns: URL patterns to add
        """
        if scraper_type not in self.config.url_patterns:
            self.config.url_patterns[scraper_type] = []
        
        self.config.url_patterns[scraper_type].extend(patterns)
        logger.info(f"Added {len(patterns)} URL patterns for {scraper_type.value}")
    
    def create_scraper_from_url(self, url: str, **kwargs) -> BaseScraper:
        """Create appropriate scraper based on URL.
        
        Args:
            url: URL to determine scraper type for
            **kwargs: Configuration overrides
        
        Returns:
            Appropriate scraper for the URL
        """
        # Determine scraper type based on URL
        scraper_type = self._determine_scraper_type(url)
        return self.create_scraper(scraper_type, **kwargs)
    
    def _determine_scraper_type(self, url: str) -> ScraperType:
        """Determine appropriate scraper type for URL.
        
        Args:
            url: URL to analyze
        
        Returns:
            Appropriate scraper type
        """
        url_lower = url.lower()
        
        # Check for n8n URLs
        if 'n8n.io' in url_lower:
            return ScraperType.N8N
        
        # Check for documentation patterns
        doc_patterns = ['/docs/', '/documentation/', '/guide/', '/manual/']
        if any(pattern in url_lower for pattern in doc_patterns):
            return ScraperType.DOCUMENTATION
        
        # Check for API documentation
        api_patterns = ['/api/', '/reference/']
        if any(pattern in url_lower for pattern in api_patterns):
            return ScraperType.API_DOCS
        
        # Check for blog patterns
        blog_patterns = ['/blog/', '/post/', '/article/']
        if any(pattern in url_lower for pattern in blog_patterns):
            return ScraperType.BLOG
        
        # Default to generic
        return ScraperType.GENERIC


# Global factory instance
_default_factory: Optional[ScraperFactory] = None


def get_scraper_factory() -> ScraperFactory:
    """Get the default scraper factory instance.
    
    Returns:
        Default scraper factory
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = ScraperFactory()
    return _default_factory


def set_scraper_factory(factory: ScraperFactory) -> None:
    """Set the default scraper factory instance.
    
    Args:
        factory: Scraper factory to set as default
    """
    global _default_factory
    _default_factory = factory


def create_scraper(scraper_type: ScraperType, **kwargs) -> BaseScraper:
    """Create a scraper using the default factory.
    
    Args:
        scraper_type: Type of scraper to create
        **kwargs: Configuration overrides
    
    Returns:
        Configured scraper instance
    """
    return get_scraper_factory().create_scraper(scraper_type, **kwargs)


def create_scraper_from_url(url: str, **kwargs) -> BaseScraper:
    """Create appropriate scraper for URL using the default factory.
    
    Args:
        url: URL to create scraper for
        **kwargs: Configuration overrides
    
    Returns:
        Appropriate scraper for the URL
    """
    return get_scraper_factory().create_scraper_from_url(url, **kwargs)