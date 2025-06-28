"""
Web scraping module for n8n documentation.

This module provides comprehensive web scraping capabilities for n8n documentation,
including content extraction, processing, and storage.
"""

from .base_scraper import BaseScraper, ScrapingResult
from .n8n_scraper import N8nScraper
from .content_processor import ContentProcessor, ProcessingResult
from .rate_limiter import RateLimiter, RateLimitConfig
from .session_manager import SessionManager
from .url_manager import URLManager, URLPattern
from .content_extractor import ContentExtractor, ExtractedContent
from .quality_checker import QualityChecker, QualityMetrics
from .scraper_factory import ScraperFactory

__all__ = [
    # Base classes
    "BaseScraper",
    "ScrapingResult",
    
    # Main scraper
    "N8nScraper",
    
    # Content processing
    "ContentProcessor",
    "ProcessingResult",
    "ContentExtractor",
    "ExtractedContent",
    "QualityChecker",
    "QualityMetrics",
    
    # Utilities
    "RateLimiter",
    "RateLimitConfig",
    "SessionManager",
    "URLManager",
    "URLPattern",
    "ScraperFactory",
]