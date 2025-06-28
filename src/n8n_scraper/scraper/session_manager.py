"""
HTTP session management for web scraping.
"""

import asyncio
import ssl
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Union
from urllib.parse import urlparse

import aiohttp
import certifi

from config.settings import settings
from ..core.exceptions import ScrapingError, ConfigurationError
from ..core.logging_config import get_logger
from ..core.metrics import metrics

logger = get_logger(__name__)


@dataclass
class ProxyConfig:
    """Proxy configuration."""
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    
    def to_aiohttp_proxy(self) -> Union[str, aiohttp.BasicAuth]:
        """Convert to aiohttp proxy format.
        
        Returns:
            Proxy URL or BasicAuth object
        """
        if self.username and self.password:
            return aiohttp.BasicAuth(self.username, self.password)
        return self.url


@dataclass
class SessionConfig:
    """Configuration for HTTP sessions."""
    # Connection settings
    connector_limit: int = 100
    connector_limit_per_host: int = 30
    connector_ttl_dns_cache: int = 300
    connector_use_dns_cache: bool = True
    
    # Timeout settings
    total_timeout: float = 300.0
    connect_timeout: float = 30.0
    sock_read_timeout: float = 30.0
    sock_connect_timeout: float = 30.0
    
    # SSL settings
    verify_ssl: bool = True
    ssl_context: Optional[ssl.SSLContext] = None
    
    # Headers
    user_agent: str = "n8n-scraper/1.0 (+https://github.com/n8n-io/n8n)"
    default_headers: Dict[str, str] = field(default_factory=dict)
    
    # Cookies
    cookie_jar: Optional[aiohttp.CookieJar] = None
    
    # Proxy settings
    proxy: Optional[ProxyConfig] = None
    
    # Retry settings
    max_redirects: int = 10
    
    # Connection pooling
    keepalive_timeout: float = 30.0
    enable_cleanup_closed: bool = True
    
    def __post_init__(self):
        """Initialize default headers and SSL context."""
        if not self.default_headers:
            self.default_headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0",
            }
        
        if self.verify_ssl and self.ssl_context is None:
            self.ssl_context = ssl.create_default_context(cafile=certifi.where())
            self.ssl_context.check_hostname = True
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED


class SessionManager:
    """Manages HTTP sessions for web scraping."""
    
    def __init__(self, config: Optional[SessionConfig] = None):
        """Initialize session manager.
        
        Args:
            config: Session configuration
        """
        self.config = config or SessionConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.connector: Optional[aiohttp.TCPConnector] = None
        self._closed = False
        self._session_stats = {
            "requests_made": 0,
            "bytes_downloaded": 0,
            "connections_created": 0,
            "dns_lookups": 0,
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _create_connector(self) -> aiohttp.TCPConnector:
        """Create TCP connector with configuration.
        
        Returns:
            Configured TCP connector
        """
        connector = aiohttp.TCPConnector(
            limit=self.config.connector_limit,
            limit_per_host=self.config.connector_limit_per_host,
            ttl_dns_cache=self.config.connector_ttl_dns_cache,
            use_dns_cache=self.config.connector_use_dns_cache,
            ssl=self.config.ssl_context if self.config.verify_ssl else False,
            keepalive_timeout=self.config.keepalive_timeout,
            enable_cleanup_closed=self.config.enable_cleanup_closed,
        )
        
        logger.info(
            f"Created TCP connector: limit={self.config.connector_limit}, "
            f"per_host={self.config.connector_limit_per_host}, "
            f"ssl_verify={self.config.verify_ssl}"
        )
        
        return connector
    
    def _create_timeout(self) -> aiohttp.ClientTimeout:
        """Create timeout configuration.
        
        Returns:
            Configured timeout
        """
        return aiohttp.ClientTimeout(
            total=self.config.total_timeout,
            connect=self.config.connect_timeout,
            sock_read=self.config.sock_read_timeout,
            sock_connect=self.config.sock_connect_timeout,
        )
    
    async def start(self) -> None:
        """Start the session manager."""
        if self.session is not None:
            logger.warning("Session manager already started")
            return
        
        try:
            # Create connector
            self.connector = self._create_connector()
            
            # Create timeout
            timeout = self._create_timeout()
            
            # Create cookie jar if not provided
            cookie_jar = self.config.cookie_jar
            if cookie_jar is None:
                cookie_jar = aiohttp.CookieJar()
            
            # Create session
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=timeout,
                headers=self.config.default_headers,
                cookie_jar=cookie_jar,
            )
            
            self._closed = False
            
            logger.info("Session manager started successfully")
            metrics.increment_counter("session_manager_started")
            
        except Exception as e:
            logger.error(f"Failed to start session manager: {e}")
            metrics.increment_counter("session_manager_start_errors")
            raise ScrapingError(f"Failed to start session manager: {str(e)}") from e
    
    async def close(self) -> None:
        """Close the session manager."""
        if self._closed:
            return
        
        try:
            if self.session:
                await self.session.close()
                self.session = None
            
            if self.connector:
                await self.connector.close()
                self.connector = None
            
            self._closed = True
            
            logger.info("Session manager closed successfully")
            metrics.increment_counter("session_manager_closed")
            
        except Exception as e:
            logger.error(f"Error closing session manager: {e}")
            metrics.increment_counter("session_manager_close_errors")
    
    def is_active(self) -> bool:
        """Check if session manager is active.
        
        Returns:
            True if session is active
        """
        return not self._closed and self.session is not None and not self.session.closed
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get the current session.
        
        Returns:
            Active client session
        
        Raises:
            ScrapingError: If session is not active
        """
        if not self.is_active():
            raise ScrapingError("Session manager is not active")
        
        return self.session
    
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make an HTTP request.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters
        
        Returns:
            HTTP response
        
        Raises:
            ScrapingError: If request fails
        """
        session = await self.get_session()
        
        # Add proxy if configured
        if self.config.proxy:
            kwargs["proxy"] = self.config.proxy.url
            if self.config.proxy.username and self.config.proxy.password:
                kwargs["proxy_auth"] = aiohttp.BasicAuth(
                    self.config.proxy.username,
                    self.config.proxy.password
                )
        
        # Set max redirects
        kwargs.setdefault("max_redirects", self.config.max_redirects)
        
        try:
            response = await session.request(method, url, **kwargs)
            
            # Update stats
            self._session_stats["requests_made"] += 1
            
            # Track response size if available
            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    self._session_stats["bytes_downloaded"] += int(content_length)
                except ValueError:
                    pass
            
            metrics.increment_counter("session_manager_requests")
            metrics.record_histogram("session_manager_response_status", response.status)
            
            return response
            
        except Exception as e:
            metrics.increment_counter("session_manager_request_errors")
            logger.error(f"Request failed for {method} {url}: {e}")
            raise ScrapingError(f"Request failed: {str(e)}") from e
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a GET request.
        
        Args:
            url: Request URL
            **kwargs: Additional request parameters
        
        Returns:
            HTTP response
        """
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a POST request.
        
        Args:
            url: Request URL
            **kwargs: Additional request parameters
        
        Returns:
            HTTP response
        """
        return await self.request("POST", url, **kwargs)
    
    async def head(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make a HEAD request.
        
        Args:
            url: Request URL
            **kwargs: Additional request parameters
        
        Returns:
            HTTP response
        """
        return await self.request("HEAD", url, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self._session_stats.copy()
        
        if self.connector:
            stats.update({
                "connector_limit": self.connector.limit,
                "connector_limit_per_host": self.connector.limit_per_host,
                "connector_acquired_count": len(self.connector._acquired),
                "connector_acquired_per_host": dict(self.connector._acquired_per_host),
            })
        
        stats.update({
            "is_active": self.is_active(),
            "session_closed": self.session.closed if self.session else True,
            "config": {
                "connector_limit": self.config.connector_limit,
                "connector_limit_per_host": self.config.connector_limit_per_host,
                "total_timeout": self.config.total_timeout,
                "verify_ssl": self.config.verify_ssl,
                "proxy_enabled": self.config.proxy is not None,
            }
        })
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset session statistics."""
        self._session_stats = {
            "requests_made": 0,
            "bytes_downloaded": 0,
            "connections_created": 0,
            "dns_lookups": 0,
        }
        
        logger.info("Session statistics reset")
    
    async def update_headers(self, headers: Dict[str, str]) -> None:
        """Update default headers.
        
        Args:
            headers: Headers to update
        """
        if not self.is_active():
            raise ScrapingError("Session manager is not active")
        
        self.session.headers.update(headers)
        logger.info(f"Updated session headers: {list(headers.keys())}")
    
    async def clear_cookies(self) -> None:
        """Clear all cookies."""
        if not self.is_active():
            raise ScrapingError("Session manager is not active")
        
        self.session.cookie_jar.clear()
        logger.info("Cleared all cookies")
    
    async def get_cookies(self, url: Optional[str] = None) -> Dict[str, str]:
        """Get cookies.
        
        Args:
            url: URL to filter cookies for (optional)
        
        Returns:
            Dictionary of cookies
        """
        if not self.is_active():
            raise ScrapingError("Session manager is not active")
        
        cookies = {}
        
        if url:
            # Filter cookies for specific URL
            for cookie in self.session.cookie_jar:
                if cookie.key and cookie.value:
                    cookies[cookie.key] = cookie.value
        else:
            # Get all cookies
            for cookie in self.session.cookie_jar:
                if cookie.key and cookie.value:
                    cookies[cookie.key] = cookie.value
        
        return cookies
    
    async def set_cookies(self, cookies: Dict[str, str], url: Optional[str] = None) -> None:
        """Set cookies.
        
        Args:
            cookies: Cookies to set
            url: URL to associate cookies with (optional)
        """
        if not self.is_active():
            raise ScrapingError("Session manager is not active")
        
        if url:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            for name, value in cookies.items():
                self.session.cookie_jar.update_cookies(
                    {name: value},
                    response_url=aiohttp.URL(url)
                )
        else:
            # Set cookies without specific domain
            for name, value in cookies.items():
                self.session.cookie_jar.update_cookies({name: value})
        
        logger.info(f"Set {len(cookies)} cookies")
    
    async def check_connectivity(self, test_url: str = "https://httpbin.org/get") -> bool:
        """Check internet connectivity.
        
        Args:
            test_url: URL to test connectivity with
        
        Returns:
            True if connectivity is available
        """
        try:
            async with await self.get(test_url) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"Connectivity check failed: {e}")
            return False
    
    async def warm_up_connections(self, urls: List[str]) -> None:
        """Warm up connections to specified URLs.
        
        Args:
            urls: URLs to warm up connections for
        """
        if not self.is_active():
            raise ScrapingError("Session manager is not active")
        
        logger.info(f"Warming up connections to {len(urls)} URLs")
        
        tasks = []
        for url in urls:
            task = asyncio.create_task(self._warm_up_connection(url))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for result in results if not isinstance(result, Exception))
        logger.info(f"Warmed up {successful}/{len(urls)} connections")
    
    async def _warm_up_connection(self, url: str) -> None:
        """Warm up connection to a single URL.
        
        Args:
            url: URL to warm up connection for
        """
        try:
            async with await self.head(url) as response:
                logger.debug(f"Warmed up connection to {url}: {response.status}")
        except Exception as e:
            logger.debug(f"Failed to warm up connection to {url}: {e}")


# Global session manager instance
_global_session_manager: Optional[SessionManager] = None


async def get_global_session_manager() -> SessionManager:
    """Get or create global session manager.
    
    Returns:
        Global session manager instance
    """
    global _global_session_manager
    
    if _global_session_manager is None or not _global_session_manager.is_active():
        config = SessionConfig(
            connector_limit=settings.max_concurrent_requests,
            total_timeout=settings.request_timeout,
            verify_ssl=True,
        )
        
        _global_session_manager = SessionManager(config)
        await _global_session_manager.start()
    
    return _global_session_manager


async def close_global_session_manager() -> None:
    """Close global session manager."""
    global _global_session_manager
    
    if _global_session_manager:
        await _global_session_manager.close()
        _global_session_manager = None