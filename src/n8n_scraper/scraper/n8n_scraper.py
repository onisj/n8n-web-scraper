"""N8n-specific web scraper implementation."""

import asyncio
import re
from typing import List, Dict, Any, Optional, Set, AsyncGenerator
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field

from ..core.logging_config import get_logger
from ..core.metrics import MetricsCollector
from ..core.exceptions import ScrapingError, ValidationError
from .base_scraper import (
    BaseScraper, ScrapingResult, ScrapingMetadata, 
    ScrapingStatus, ContentType, ScrapingConfig
)
from .content_extractor import ExtractedContent
from .url_manager import URLType, Priority

logger = get_logger(__name__)
metrics = MetricsCollector()


@dataclass
class N8nScrapingConfig(ScrapingConfig):
    """N8n-specific scraping configuration."""
    # N8n-specific settings
    scrape_integrations: bool = True
    scrape_code_examples: bool = True
    scrape_api_docs: bool = True
    scrape_tutorials: bool = True
    scrape_changelog: bool = False
    scrape_blog: bool = False
    scrape_community: bool = False
    
    # Content filtering
    min_integration_content_length: int = 200
    min_tutorial_content_length: int = 500
    min_api_doc_content_length: int = 100
    
    # Specific URL patterns to prioritize
    priority_paths: List[str] = field(default_factory=lambda: [
        '/integrations/',
        '/code/',
        '/api/',
        '/tutorials/',
        '/getting-started/',
        '/workflows/',
        '/nodes/',
    ])
    
    # Paths to exclude
    excluded_paths: List[str] = field(default_factory=lambda: [
        '/community/',
        '/changelog/',
        '/blog/',
        '/search',
        '/404',
        '/login',
        '/signup',
    ])


class N8nScraper(BaseScraper):
    """Scraper specifically designed for n8n documentation and resources."""
    
    def __init__(self, 
                 config: Optional[N8nScrapingConfig] = None,
                 **kwargs):
        """Initialize N8n scraper.
        
        Args:
            config: N8n-specific scraping configuration
            **kwargs: Additional configuration parameters
        """
        self.n8n_config = config or N8nScrapingConfig()
        super().__init__(config=self.n8n_config, **kwargs)
        
        # N8n-specific patterns
        self.integration_patterns = [
            r'/integrations/[^/]+/?$',
            r'/integrations/builtin/[^/]+/?$',
            r'/integrations/community-nodes/[^/]+/?$',
        ]
        
        self.code_example_patterns = [
            r'/code/[^/]+/?$',
            r'/code/examples/[^/]+/?$',
            r'/workflows/[^/]+/?$',
        ]
        
        self.api_doc_patterns = [
            r'/api/[^/]+/?$',
            r'/reference/[^/]+/?$',
        ]
        
        self.tutorial_patterns = [
            r'/tutorials/[^/]+/?$',
            r'/getting-started/[^/]+/?$',
            r'/courses/[^/]+/?$',
        ]
        
        # Content selectors specific to n8n docs
        self.n8n_selectors = {
            'main_content': [
                'main[role="main"]',
                '.main-content',
                '.content',
                '.documentation-content',
                'article',
                '.markdown-body',
            ],
            'navigation': [
                '.sidebar',
                '.navigation',
                '.toc',
                '.table-of-contents',
            ],
            'code_blocks': [
                'pre code',
                '.highlight',
                '.code-block',
                '.language-javascript',
                '.language-json',
                '.language-typescript',
            ],
            'integration_info': [
                '.integration-header',
                '.node-info',
                '.integration-details',
            ],
            'examples': [
                '.example',
                '.workflow-example',
                '.code-example',
            ],
        }
    
    async def scrape_url(self, url: str) -> ScrapingResult:
        """Scrape a single URL with n8n-specific processing.
        
        Args:
            url: URL to scrape
        
        Returns:
            Scraping result with n8n-specific metadata
        """
        try:
            # Check if URL should be scraped based on n8n config
            if not self._should_scrape_n8n_url(url):
                return ScrapingResult(
                    url=url,
                    status=ScrapingStatus.SKIPPED,
                    metadata=ScrapingMetadata(
                        content_type=ContentType.HTML,
                        reason="URL excluded by n8n configuration"
                    )
                )
            
            # Use base scraper functionality
            result = await super().scrape_url(url)
            
            # Add n8n-specific processing
            if result.status == ScrapingStatus.SUCCESS and result.content:
                result = await self._enhance_n8n_content(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error scraping n8n URL {url}: {str(e)}")
            metrics.increment('n8n_scraper.errors', {'url': url, 'error': type(e).__name__})
            
            return ScrapingResult(
                url=url,
                status=ScrapingStatus.FAILED,
                metadata=ScrapingMetadata(
                    content_type=ContentType.HTML,
                    error=str(e)
                )
            )
    
    def _should_scrape_n8n_url(self, url: str) -> bool:
        """Check if URL should be scraped based on n8n configuration.
        
        Args:
            url: URL to check
        
        Returns:
            True if URL should be scraped
        """
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Check excluded paths
        for excluded_path in self.n8n_config.excluded_paths:
            if excluded_path.lower() in path:
                return False
        
        # Check specific content type settings
        if not self.n8n_config.scrape_integrations and '/integrations/' in path:
            return False
        
        if not self.n8n_config.scrape_code_examples and ('/code/' in path or '/workflows/' in path):
            return False
        
        if not self.n8n_config.scrape_api_docs and ('/api/' in path or '/reference/' in path):
            return False
        
        if not self.n8n_config.scrape_tutorials and ('/tutorials/' in path or '/getting-started/' in path):
            return False
        
        if not self.n8n_config.scrape_changelog and '/changelog/' in path:
            return False
        
        if not self.n8n_config.scrape_blog and '/blog/' in path:
            return False
        
        if not self.n8n_config.scrape_community and '/community/' in path:
            return False
        
        return True
    
    async def _enhance_n8n_content(self, result: ScrapingResult) -> ScrapingResult:
        """Enhance scraping result with n8n-specific processing.
        
        Args:
            result: Original scraping result
        
        Returns:
            Enhanced scraping result
        """
        try:
            if not result.content or not result.content.content:
                return result
            
            # Determine content type
            url_type = self._classify_n8n_url(result.url)
            
            # Extract n8n-specific information
            n8n_metadata = await self._extract_n8n_metadata(result.content, url_type)
            
            # Update metadata
            if result.metadata.custom_data is None:
                result.metadata.custom_data = {}
            
            result.metadata.custom_data.update({
                'n8n_url_type': url_type.value if url_type else 'unknown',
                'n8n_metadata': n8n_metadata,
            })
            
            # Apply content length filters
            if not self._meets_content_requirements(result.content, url_type):
                result.status = ScrapingStatus.SKIPPED
                result.metadata.reason = "Content does not meet n8n requirements"
            
            return result
            
        except Exception as e:
            logger.error(f"Error enhancing n8n content for {result.url}: {str(e)}")
            return result
    
    def _classify_n8n_url(self, url: str) -> Optional[URLType]:
        """Classify n8n URL type.
        
        Args:
            url: URL to classify
        
        Returns:
            URL type or None if not classified
        """
        path = urlparse(url).path.lower()
        
        # Check integration patterns
        for pattern in self.integration_patterns:
            if re.search(pattern, path):
                return URLType.INTEGRATION
        
        # Check code example patterns
        for pattern in self.code_example_patterns:
            if re.search(pattern, path):
                return URLType.CODE_EXAMPLE
        
        # Check API documentation patterns
        for pattern in self.api_doc_patterns:
            if re.search(pattern, path):
                return URLType.API_REFERENCE
        
        # Check tutorial patterns
        for pattern in self.tutorial_patterns:
            if re.search(pattern, path):
                return URLType.TUTORIAL
        
        # Default classifications
        if '/docs/' in path:
            return URLType.DOCUMENTATION
        elif '/blog/' in path:
            return URLType.BLOG_POST
        elif '/community/' in path:
            return URLType.FORUM_POST
        
        return URLType.GENERAL
    
    async def _extract_n8n_metadata(self, 
                                   content: ExtractedContent, 
                                   url_type: Optional[URLType]) -> Dict[str, Any]:
        """Extract n8n-specific metadata from content.
        
        Args:
            content: Extracted content
            url_type: Type of URL
        
        Returns:
            N8n-specific metadata
        """
        metadata = {
            'url_type': url_type.value if url_type else 'unknown',
            'has_code_examples': bool(content.code_blocks),
            'code_languages': [],
            'integration_info': {},
            'workflow_info': {},
            'api_info': {},
        }
        
        # Extract code languages
        if content.code_blocks:
            languages = set()
            for code_block in content.code_blocks:
                if code_block.get('language'):
                    languages.add(code_block['language'])
            metadata['code_languages'] = list(languages)
        
        # Extract integration-specific information
        if url_type == URLType.INTEGRATION:
            metadata['integration_info'] = self._extract_integration_info(content)
        
        # Extract workflow information
        if url_type == URLType.CODE_EXAMPLE or 'workflow' in content.title.lower():
            metadata['workflow_info'] = self._extract_workflow_info(content)
        
        # Extract API information
        if url_type == URLType.API_REFERENCE:
            metadata['api_info'] = self._extract_api_info(content)
        
        return metadata
    
    def _extract_integration_info(self, content: ExtractedContent) -> Dict[str, Any]:
        """Extract integration-specific information.
        
        Args:
            content: Extracted content
        
        Returns:
            Integration information
        """
        info = {
            'node_type': None,
            'category': None,
            'credentials_required': False,
            'operations': [],
            'triggers': [],
        }
        
        text = content.content.lower()
        
        # Detect node type
        if 'trigger node' in text:
            info['node_type'] = 'trigger'
        elif 'regular node' in text:
            info['node_type'] = 'regular'
        
        # Detect if credentials are required
        if any(term in text for term in ['credentials', 'authentication', 'api key', 'token']):
            info['credentials_required'] = True
        
        # Extract operations from headings
        operations = []
        for heading in content.headings:
            heading_text = heading.get('text', '').lower()
            if any(op in heading_text for op in ['create', 'read', 'update', 'delete', 'get', 'post', 'put']):
                operations.append(heading.get('text', ''))
        
        info['operations'] = operations[:10]  # Limit to 10 operations
        
        return info
    
    def _extract_workflow_info(self, content: ExtractedContent) -> Dict[str, Any]:
        """Extract workflow-specific information.
        
        Args:
            content: Extracted content
        
        Returns:
            Workflow information
        """
        info = {
            'has_workflow_json': False,
            'node_count': 0,
            'workflow_complexity': 'simple',
            'use_cases': [],
        }
        
        text = content.content
        
        # Check for workflow JSON
        if 'workflow.json' in text.lower() or '"nodes":' in text:
            info['has_workflow_json'] = True
        
        # Estimate node count from content
        node_mentions = len(re.findall(r'\bnode\b', text.lower()))
        if node_mentions > 10:
            info['node_count'] = node_mentions
            info['workflow_complexity'] = 'complex' if node_mentions > 20 else 'medium'
        
        # Extract use cases from headings
        use_cases = []
        for heading in content.headings:
            heading_text = heading.get('text', '').lower()
            if any(term in heading_text for term in ['use case', 'example', 'scenario']):
                use_cases.append(heading.get('text', ''))
        
        info['use_cases'] = use_cases[:5]  # Limit to 5 use cases
        
        return info
    
    def _extract_api_info(self, content: ExtractedContent) -> Dict[str, Any]:
        """Extract API-specific information.
        
        Args:
            content: Extracted content
        
        Returns:
            API information
        """
        info = {
            'endpoints': [],
            'methods': [],
            'parameters': [],
            'response_formats': [],
        }
        
        text = content.content
        
        # Extract HTTP methods
        methods = set(re.findall(r'\b(GET|POST|PUT|DELETE|PATCH)\b', text))
        info['methods'] = list(methods)
        
        # Extract endpoints
        endpoints = re.findall(r'/api/[\w/\-{}]+', text)
        info['endpoints'] = list(set(endpoints))[:10]  # Limit and deduplicate
        
        # Extract response formats
        if 'json' in text.lower():
            info['response_formats'].append('json')
        if 'xml' in text.lower():
            info['response_formats'].append('xml')
        
        return info
    
    def _meets_content_requirements(self, 
                                  content: ExtractedContent, 
                                  url_type: Optional[URLType]) -> bool:
        """Check if content meets n8n-specific requirements.
        
        Args:
            content: Extracted content
            url_type: Type of URL
        
        Returns:
            True if content meets requirements
        """
        content_length = len(content.content)
        
        if url_type == URLType.INTEGRATION:
            return content_length >= self.n8n_config.min_integration_content_length
        elif url_type == URLType.TUTORIAL:
            return content_length >= self.n8n_config.min_tutorial_content_length
        elif url_type == URLType.API_REFERENCE:
            return content_length >= self.n8n_config.min_api_doc_content_length
        
        # Default minimum content length
        return content_length >= 100
    
    async def scrape_n8n_documentation(self, 
                                      start_urls: Optional[List[str]] = None) -> AsyncGenerator[ScrapingResult, None]:
        """Scrape n8n documentation with predefined starting points.
        
        Args:
            start_urls: Optional custom starting URLs
        
        Yields:
            Scraping results
        """
        if start_urls is None:
            start_urls = [
                'https://docs.n8n.io/',
                'https://docs.n8n.io/integrations/',
                'https://docs.n8n.io/code/',
                'https://docs.n8n.io/api/',
                'https://docs.n8n.io/tutorials/',
                'https://docs.n8n.io/getting-started/',
            ]
        
        logger.info(f"Starting n8n documentation scraping with {len(start_urls)} URLs")
        
        async for result in self.scrape_urls(start_urls):
            yield result
    
    async def scrape_n8n_integrations(self) -> AsyncGenerator[ScrapingResult, None]:
        """Scrape n8n integrations specifically.
        
        Yields:
            Scraping results for integrations
        """
        integration_urls = [
            'https://docs.n8n.io/integrations/',
            'https://docs.n8n.io/integrations/builtin/',
            'https://docs.n8n.io/integrations/community-nodes/',
        ]
        
        logger.info("Starting n8n integrations scraping")
        
        async for result in self.scrape_urls(integration_urls):
            # Only yield integration-related results
            if result.metadata.custom_data and \
               result.metadata.custom_data.get('n8n_url_type') == 'integration':
                yield result
    
    def get_n8n_statistics(self) -> Dict[str, Any]:
        """Get n8n-specific scraping statistics.
        
        Returns:
            N8n scraping statistics
        """
        stats = self.get_statistics()
        
        # Add n8n-specific stats
        n8n_stats = {
            'total_scraped': stats.get('total_scraped', 0),
            'total_failed': stats.get('total_failed', 0),
            'integrations_scraped': 0,
            'code_examples_scraped': 0,
            'api_docs_scraped': 0,
            'tutorials_scraped': 0,
        }
        
        # Count by URL type (would need to track this during scraping)
        # This is a simplified version - in practice, you'd track these during scraping
        
        return n8n_stats