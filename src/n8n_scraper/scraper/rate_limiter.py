"""
Rate limiting utilities for web scraping.
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from urllib.parse import urlparse

from ..core.exceptions import ScrapingRateLimitError
from ..core.logging_config import get_logger
from ..core.metrics import metrics

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 1.0
    requests_per_minute: int = 60
    requests_per_hour: int = 3600
    burst_size: int = 5
    backoff_factor: float = 2.0
    max_backoff_seconds: float = 300.0
    per_domain: bool = True
    respect_retry_after: bool = True
    adaptive_delay: bool = True
    min_delay_seconds: float = 0.1
    max_delay_seconds: float = 60.0
    
    def __post_init__(self):
        """Validate configuration."""
        if self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        if self.requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        if self.requests_per_hour <= 0:
            raise ValueError("requests_per_hour must be positive")
        if self.burst_size <= 0:
            raise ValueError("burst_size must be positive")


class TokenBucket:
    """Token bucket algorithm for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens.
        
        Args:
            tokens: Number of tokens to consume
        
        Returns:
            True if tokens were consumed, False otherwise
        """
        async with self._lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def wait_for_tokens(self, tokens: int = 1) -> float:
        """Wait until tokens are available.
        
        Args:
            tokens: Number of tokens needed
        
        Returns:
            Time waited in seconds
        """
        start_time = time.time()
        
        while not await self.consume(tokens):
            # Calculate wait time
            wait_time = tokens / self.refill_rate
            await asyncio.sleep(min(wait_time, 0.1))  # Sleep in small increments
        
        return time.time() - start_time
    
    def get_available_tokens(self) -> float:
        """Get current number of available tokens.
        
        Returns:
            Number of available tokens
        """
        now = time.time()
        elapsed = now - self.last_refill
        return min(self.capacity, self.tokens + elapsed * self.refill_rate)


class SlidingWindowCounter:
    """Sliding window counter for rate limiting."""
    
    def __init__(self, window_size: int, max_requests: int):
        """Initialize sliding window counter.
        
        Args:
            window_size: Window size in seconds
            max_requests: Maximum requests in window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = deque()
        self._lock = asyncio.Lock()
    
    async def can_make_request(self) -> bool:
        """Check if request can be made.
        
        Returns:
            True if request is allowed
        """
        async with self._lock:
            now = time.time()
            
            # Remove old requests outside the window
            while self.requests and self.requests[0] <= now - self.window_size:
                self.requests.popleft()
            
            # Check if we can make a new request
            return len(self.requests) < self.max_requests
    
    async def record_request(self) -> None:
        """Record a new request."""
        async with self._lock:
            now = time.time()
            
            # Remove old requests
            while self.requests and self.requests[0] <= now - self.window_size:
                self.requests.popleft()
            
            # Add new request
            self.requests.append(now)
    
    def get_request_count(self) -> int:
        """Get current request count in window.
        
        Returns:
            Number of requests in current window
        """
        now = time.time()
        
        # Count requests in current window
        count = 0
        for request_time in reversed(self.requests):
            if request_time > now - self.window_size:
                count += 1
            else:
                break
        
        return count


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on server responses."""
    
    def __init__(self, initial_delay: float = 1.0):
        """Initialize adaptive rate limiter.
        
        Args:
            initial_delay: Initial delay between requests
        """
        self.current_delay = initial_delay
        self.initial_delay = initial_delay
        self.consecutive_successes = 0
        self.consecutive_failures = 0
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()
    
    async def wait_before_request(self) -> float:
        """Wait before making a request.
        
        Returns:
            Time waited in seconds
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_request_time
            
            if elapsed < self.current_delay:
                wait_time = self.current_delay - elapsed
                await asyncio.sleep(wait_time)
                self.last_request_time = time.time()
                return wait_time
            
            self.last_request_time = now
            return 0.0
    
    async def record_success(self) -> None:
        """Record a successful request."""
        async with self._lock:
            self.consecutive_successes += 1
            self.consecutive_failures = 0
            
            # Gradually decrease delay on consecutive successes
            if self.consecutive_successes >= 5:
                self.current_delay = max(
                    self.initial_delay,
                    self.current_delay * 0.9
                )
                self.consecutive_successes = 0
    
    async def record_failure(self, is_rate_limit: bool = False) -> None:
        """Record a failed request.
        
        Args:
            is_rate_limit: Whether failure was due to rate limiting
        """
        async with self._lock:
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            
            # Increase delay on failures
            if is_rate_limit:
                self.current_delay = min(
                    300.0,  # Max 5 minutes
                    self.current_delay * 2.0
                )
            else:
                self.current_delay = min(
                    60.0,  # Max 1 minute for non-rate-limit failures
                    self.current_delay * 1.5
                )
    
    def get_current_delay(self) -> float:
        """Get current delay.
        
        Returns:
            Current delay in seconds
        """
        return self.current_delay


class RateLimiter:
    """Comprehensive rate limiter for web scraping."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config or RateLimitConfig()
        
        # Per-domain rate limiters if enabled
        self.domain_limiters: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Global rate limiter
        self.global_token_bucket = TokenBucket(
            capacity=self.config.burst_size,
            refill_rate=self.config.requests_per_second
        )
        
        self.global_minute_counter = SlidingWindowCounter(
            window_size=60,
            max_requests=self.config.requests_per_minute
        )
        
        self.global_hour_counter = SlidingWindowCounter(
            window_size=3600,
            max_requests=self.config.requests_per_hour
        )
        
        # Adaptive rate limiting
        self.adaptive_limiters: Dict[str, AdaptiveRateLimiter] = {}
        
        # Retry-After tracking
        self.retry_after_times: Dict[str, float] = {}
        
        self._lock = asyncio.Lock()
    
    def _get_domain(self, url: str) -> str:
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
    
    def _get_domain_limiters(self, domain: str) -> Dict[str, Any]:
        """Get or create rate limiters for a domain.
        
        Args:
            domain: Domain name
        
        Returns:
            Dictionary of rate limiters for the domain
        """
        if domain not in self.domain_limiters:
            self.domain_limiters[domain] = {
                "token_bucket": TokenBucket(
                    capacity=self.config.burst_size,
                    refill_rate=self.config.requests_per_second
                ),
                "minute_counter": SlidingWindowCounter(
                    window_size=60,
                    max_requests=self.config.requests_per_minute
                ),
                "hour_counter": SlidingWindowCounter(
                    window_size=3600,
                    max_requests=self.config.requests_per_hour
                ),
            }
        
        return self.domain_limiters[domain]
    
    def _get_adaptive_limiter(self, domain: str) -> AdaptiveRateLimiter:
        """Get or create adaptive rate limiter for a domain.
        
        Args:
            domain: Domain name
        
        Returns:
            Adaptive rate limiter for the domain
        """
        if domain not in self.adaptive_limiters:
            self.adaptive_limiters[domain] = AdaptiveRateLimiter(
                initial_delay=1.0 / self.config.requests_per_second
            )
        
        return self.adaptive_limiters[domain]
    
    async def wait_if_needed(self, url: str) -> float:
        """Wait if rate limiting is needed.
        
        Args:
            url: URL being requested
        
        Returns:
            Time waited in seconds
        
        Raises:
            ScrapingRateLimitError: If rate limit cannot be satisfied
        """
        domain = self._get_domain(url)
        total_wait_time = 0.0
        
        async with self._lock:
            # Check retry-after times
            if domain in self.retry_after_times:
                retry_after_time = self.retry_after_times[domain]
                if time.time() < retry_after_time:
                    wait_time = retry_after_time - time.time()
                    logger.info(f"Waiting {wait_time:.2f}s due to Retry-After header for {domain}")
                    await asyncio.sleep(wait_time)
                    total_wait_time += wait_time
                else:
                    # Retry-after time has passed
                    del self.retry_after_times[domain]
        
        # Adaptive rate limiting
        if self.config.adaptive_delay:
            adaptive_limiter = self._get_adaptive_limiter(domain)
            wait_time = await adaptive_limiter.wait_before_request()
            total_wait_time += wait_time
        
        # Choose limiters based on configuration
        if self.config.per_domain:
            limiters = self._get_domain_limiters(domain)
            token_bucket = limiters["token_bucket"]
            minute_counter = limiters["minute_counter"]
            hour_counter = limiters["hour_counter"]
        else:
            token_bucket = self.global_token_bucket
            minute_counter = self.global_minute_counter
            hour_counter = self.global_hour_counter
        
        # Check rate limits
        start_time = time.time()
        
        # Check hourly limit
        if not await hour_counter.can_make_request():
            logger.warning(f"Hourly rate limit exceeded for {domain}")
            metrics.increment_counter("rate_limiter_hourly_limit_exceeded")
            raise ScrapingRateLimitError(f"Hourly rate limit exceeded for {domain}")
        
        # Check minute limit
        if not await minute_counter.can_make_request():
            logger.warning(f"Minute rate limit exceeded for {domain}")
            metrics.increment_counter("rate_limiter_minute_limit_exceeded")
            # Wait until next minute window
            wait_time = 60.0
            await asyncio.sleep(wait_time)
            total_wait_time += wait_time
        
        # Wait for token bucket
        wait_time = await token_bucket.wait_for_tokens(1)
        total_wait_time += wait_time
        
        # Record the request
        await minute_counter.record_request()
        await hour_counter.record_request()
        
        # Update metrics
        if total_wait_time > 0:
            metrics.record_histogram("rate_limiter_wait_time", total_wait_time)
            metrics.increment_counter("rate_limiter_requests_delayed")
        
        metrics.increment_counter("rate_limiter_requests_processed")
        
        return total_wait_time
    
    async def record_response(self, url: str, status_code: int, headers: Dict[str, str]) -> None:
        """Record response for adaptive rate limiting.
        
        Args:
            url: URL that was requested
            status_code: HTTP status code
            headers: Response headers
        """
        domain = self._get_domain(url)
        
        # Handle Retry-After header
        if self.config.respect_retry_after and "retry-after" in headers:
            try:
                retry_after = float(headers["retry-after"])
                retry_after_time = time.time() + retry_after
                
                async with self._lock:
                    self.retry_after_times[domain] = retry_after_time
                
                logger.info(f"Retry-After header received for {domain}: {retry_after}s")
                metrics.increment_counter("rate_limiter_retry_after_received")
            except (ValueError, TypeError):
                logger.warning(f"Invalid Retry-After header for {domain}: {headers['retry-after']}")
        
        # Adaptive rate limiting
        if self.config.adaptive_delay:
            adaptive_limiter = self._get_adaptive_limiter(domain)
            
            if status_code == 429:  # Too Many Requests
                await adaptive_limiter.record_failure(is_rate_limit=True)
                metrics.increment_counter("rate_limiter_429_responses")
            elif 500 <= status_code < 600:  # Server errors
                await adaptive_limiter.record_failure(is_rate_limit=False)
            elif 200 <= status_code < 300:  # Success
                await adaptive_limiter.record_success()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            "config": {
                "requests_per_second": self.config.requests_per_second,
                "requests_per_minute": self.config.requests_per_minute,
                "requests_per_hour": self.config.requests_per_hour,
                "burst_size": self.config.burst_size,
                "per_domain": self.config.per_domain,
                "adaptive_delay": self.config.adaptive_delay,
            },
            "global": {
                "available_tokens": self.global_token_bucket.get_available_tokens(),
                "minute_requests": self.global_minute_counter.get_request_count(),
                "hour_requests": self.global_hour_counter.get_request_count(),
            },
            "domains": {},
            "retry_after_domains": len(self.retry_after_times),
        }
        
        # Add per-domain stats
        for domain, limiters in self.domain_limiters.items():
            stats["domains"][domain] = {
                "available_tokens": limiters["token_bucket"].get_available_tokens(),
                "minute_requests": limiters["minute_counter"].get_request_count(),
                "hour_requests": limiters["hour_counter"].get_request_count(),
            }
            
            if domain in self.adaptive_limiters:
                stats["domains"][domain]["current_delay"] = self.adaptive_limiters[domain].get_current_delay()
        
        return stats
    
    def reset_domain_limits(self, domain: str) -> None:
        """Reset rate limits for a specific domain.
        
        Args:
            domain: Domain to reset limits for
        """
        if domain in self.domain_limiters:
            del self.domain_limiters[domain]
        
        if domain in self.adaptive_limiters:
            del self.adaptive_limiters[domain]
        
        if domain in self.retry_after_times:
            del self.retry_after_times[domain]
        
        logger.info(f"Reset rate limits for domain: {domain}")
    
    def reset_all_limits(self) -> None:
        """Reset all rate limits."""
        self.domain_limiters.clear()
        self.adaptive_limiters.clear()
        self.retry_after_times.clear()
        
        # Reset global limiters
        self.global_token_bucket = TokenBucket(
            capacity=self.config.burst_size,
            refill_rate=self.config.requests_per_second
        )
        
        self.global_minute_counter = SlidingWindowCounter(
            window_size=60,
            max_requests=self.config.requests_per_minute
        )
        
        self.global_hour_counter = SlidingWindowCounter(
            window_size=3600,
            max_requests=self.config.requests_per_hour
        )
        
        logger.info("Reset all rate limits")