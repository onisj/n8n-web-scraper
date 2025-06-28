"""CORS Middleware

Custom CORS middleware for the n8n AI Knowledge System API
"""

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware
from typing import List, Optional
import os

class CORSMiddleware:
    """Custom CORS middleware with environment-based configuration"""
    
    def __init__(
        self,
        allow_origins: Optional[List[str]] = None,
        allow_credentials: bool = True,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        expose_headers: Optional[List[str]] = None,
        max_age: int = 600
    ):
        # Get CORS settings from environment or use defaults
        self.allow_origins = allow_origins or self._get_allowed_origins()
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods or [
            "GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"
        ]
        self.allow_headers = allow_headers or [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-API-Key"
        ]
        self.expose_headers = expose_headers or [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ]
        self.max_age = max_age
    
    def _get_allowed_origins(self) -> List[str]:
        """Get allowed origins from environment"""
        origins_env = os.getenv("CORS_ORIGINS", "*")
        
        if origins_env == "*":
            return ["*"]
        
        # Parse comma-separated origins
        origins = [origin.strip() for origin in origins_env.split(",")]
        
        # Add common development origins if in development mode
        if os.getenv("ENVIRONMENT", "development") == "development":
            dev_origins = [
                "http://localhost:3000",
                "http://localhost:8501",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8501"
            ]
            origins.extend(dev_origins)
        
        return list(set(origins))  # Remove duplicates
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed"""
        if "*" in self.allow_origins:
            return True
        
        return origin in self.allow_origins
    
    async def __call__(self, request: Request, call_next):
        """Process CORS for incoming requests"""
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            
            if origin and self._is_origin_allowed(origin):
                response.headers["Access-Control-Allow-Origin"] = origin
            elif "*" in self.allow_origins:
                response.headers["Access-Control-Allow-Origin"] = "*"
            
            if self.allow_credentials and origin:
                response.headers["Access-Control-Allow-Credentials"] = "true"
            
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
            response.headers["Access-Control-Max-Age"] = str(self.max_age)
            
            return response
        
        # Process actual request
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin and self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        if self.allow_credentials and origin:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        if self.expose_headers:
            response.headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
        
        return response

def get_cors_middleware():
    """Get configured CORS middleware for FastAPI"""
    return FastAPICORSMiddleware(
        allow_origins=CORSMiddleware()._get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ]
    )

# CORS configuration for different environments
CORS_CONFIGS = {
    "development": {
        "allow_origins": [
            "http://localhost:3000",
            "http://localhost:8501",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8501"
        ],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"]
    },
    "production": {
        "allow_origins": [],  # Should be set via environment
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": [
            "Accept",
            "Content-Type",
            "Authorization",
            "X-API-Key"
        ]
    }
}

def get_cors_config(environment: str = None):
    """Get CORS configuration for specific environment"""
    env = environment or os.getenv("ENVIRONMENT", "development")
    return CORS_CONFIGS.get(env, CORS_CONFIGS["development"])