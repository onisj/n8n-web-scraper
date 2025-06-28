"""Rate Limiting Middleware

Provides rate limiting functionality for the API
"""

from fastapi import Request, HTTPException, status
from typing import Dict, Optional
import time
from collections import defaultdict, deque
import asyncio

class RateLimitMiddleware:
    """Rate limiting middleware using token bucket algorithm"""
    
    def __init__(
        self,
        calls: int = 100,
        period: int = 60,
        per_ip: bool = True
    ):
        """
        Initialize rate limiter
        
        Args:
            calls: Number of calls allowed
            period: Time period in seconds
            per_ip: Whether to apply rate limiting per IP
        """
        self.calls = calls
        self.period = period
        self.per_ip = per_ip
        self.clients: Dict[str, deque] = defaultdict(deque)
        self.lock = asyncio.Lock()
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        if self.per_ip:
            # Get real IP from headers (considering proxies)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()
            
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip
            
            return request.client.host if request.client else "unknown"
        else:
            return "global"
    
    async def __call__(self, request: Request):
        """Process rate limiting for incoming requests"""
        # Skip rate limiting for health check
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return
        
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        async with self.lock:
            # Get client's request history
            client_requests = self.clients[client_id]
            
            # Remove old requests outside the time window
            while client_requests and client_requests[0] <= current_time - self.period:
                client_requests.popleft()
            
            # Check if client has exceeded rate limit
            if len(client_requests) >= self.calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {self.calls} requests per {self.period} seconds.",
                    headers={
                        "X-RateLimit-Limit": str(self.calls),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(client_requests[0] + self.period))
                    }
                )
            
            # Add current request to history
            client_requests.append(current_time)
            
            # Add rate limit headers to response
            remaining = self.calls - len(client_requests)
            reset_time = int(current_time + self.period)
            
            # Store headers in request state for response
            request.state.rate_limit_headers = {
                "X-RateLimit-Limit": str(self.calls),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time)
            }

class AdvancedRateLimiter:
    """Advanced rate limiter with different limits for different endpoints"""
    
    def __init__(self):
        self.limiters = {
            "/ai/": RateLimitMiddleware(calls=50, period=60),  # AI endpoints
            "/knowledge/search": RateLimitMiddleware(calls=100, period=60),  # Search
            "/system/": RateLimitMiddleware(calls=20, period=60),  # System endpoints
            "default": RateLimitMiddleware(calls=100, period=60)  # Default
        }
    
    async def __call__(self, request: Request):
        """Apply appropriate rate limiting based on endpoint"""
        path = request.url.path
        
        # Find matching limiter
        limiter = None
        for pattern, rate_limiter in self.limiters.items():
            if pattern != "default" and path.startswith(pattern):
                limiter = rate_limiter
                break
        
        # Use default if no specific limiter found
        if not limiter:
            limiter = self.limiters["default"]
        
        await limiter(request)

# Simple decorator for route-level rate limiting
def rate_limit(calls: int = 10, period: int = 60):
    """Decorator for applying rate limiting to specific routes"""
    limiter = RateLimitMiddleware(calls=calls, period=period)
    
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            await limiter(request)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator