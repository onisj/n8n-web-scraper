"""Authentication Middleware

Provides API key authentication and JWT user authentication for the n8n AI Knowledge System"""

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Union
import os
import logging

from ...auth.jwt_auth import get_jwt_manager, AuthenticationError, InvalidTokenError
from ...database.user_service import get_user_service
from ...database.connection import get_db_session
from ..models.user import UserResponse

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Authentication middleware for API endpoints"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("API_KEY")
        self.security = HTTPBearer(auto_error=False)
    
    async def __call__(self, request: Request):
        """Process authentication for incoming requests"""
        # Skip authentication for health check and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return
        
        # Skip if no API key is configured
        if not self.api_key:
            return
        
        # Get authorization header
        authorization: HTTPAuthorizationCredentials = await self.security(request)
        
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validate API key
        if authorization.credentials != self.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"}
            )

# Enhanced authentication dependencies
security = HTTPBearer(auto_error=False)

async def get_current_user_or_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Union[UserResponse, str]]:
    """Dependency that accepts either JWT user token or API key"""
    if not credentials:
        return None
    
    token = credentials.credentials
    
    # First try JWT authentication
    try:
        jwt_manager = get_jwt_manager()
        token_data = jwt_manager.extract_token_data(token)
        
        if token_data and token_data.user_id:
            # Check if token is revoked
            if not await jwt_manager.is_token_revoked(token):
                # Get user from database
                user_service = get_user_service()
                user = await user_service.get_user_by_id(int(token_data.user_id))
                if user and user.is_active:
                    return user
    except Exception as e:
        logger.debug(f"JWT authentication failed: {str(e)}")
    
    # Fallback to API key authentication
    api_key = os.getenv("API_KEY")
    if api_key and token == api_key:
        return "api_key"
    
    return None

async def require_auth(
    auth_result: Optional[Union[UserResponse, str]] = Depends(get_current_user_or_api_key)
) -> Union[UserResponse, str]:
    """Dependency that requires either valid JWT or API key"""
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide either a valid JWT token or API key.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return auth_result

async def require_user_auth(
    auth_result: Optional[Union[UserResponse, str]] = Depends(get_current_user_or_api_key)
) -> UserResponse:
    """Dependency that requires valid JWT user authentication (not API key)"""
    if not isinstance(auth_result, UserResponse):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return auth_result

# Legacy dependency function for backward compatibility
def get_api_key(credentials: HTTPAuthorizationCredentials = HTTPBearer()):
    """Legacy dependency to validate API key for specific routes"""
    api_key = os.getenv("API_KEY")
    
    if not api_key:
        return True  # No authentication required
    
    if credentials.credentials != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return True