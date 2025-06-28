"""JWT Authentication utilities for the n8n AI Knowledge System"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from pydantic import ValidationError

from ..api.models.user import TokenData, UserResponse
from ..cache.redis_cache import get_cache, cache_key_for_session

logger = logging.getLogger(__name__)

class JWTManager:
    """JWT token management"""
    
    def __init__(self):
        self.secret_key = os.getenv("API_SECRET_KEY", "your_secret_key_here_change_this_in_production")
        self.algorithm = os.getenv("AUTH_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("API_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        
        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Validate configuration
        if self.secret_key == "your_secret_key_here_change_this_in_production":
            logger.warning("Using default secret key! Change API_SECRET_KEY in production!")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type:
                logger.warning(f"Invalid token type. Expected: {token_type}, Got: {payload.get('type')}")
                return None
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                logger.warning("Token has expired")
                return None
            
            return payload
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {str(e)}")
            return None
    
    def extract_token_data(self, token: str) -> Optional[TokenData]:
        """Extract token data from JWT"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        try:
            token_data = TokenData(
                user_id=payload.get("sub"),
                email=payload.get("email"),
                scopes=payload.get("scopes", [])
            )
            return token_data
        except ValidationError as e:
            logger.error(f"Invalid token data: {str(e)}")
            return None
    
    async def create_user_tokens(
        self, 
        user: UserResponse, 
        remember_me: bool = False
    ) -> Dict[str, Any]:
        """Create access and refresh tokens for user"""
        # Token payload
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "scopes": ["read", "write"] if user.is_active else ["read"]
        }
        
        # Create tokens
        access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
        if remember_me:
            access_token_expires = timedelta(days=1)  # Longer for remember me
        
        access_token = self.create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )
        
        refresh_token = self.create_refresh_token(data=token_data)
        
        # Cache session in Redis
        cache = await get_cache()
        session_data = {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "created_at": datetime.utcnow().isoformat(),
            "remember_me": remember_me
        }
        
        # Store session with access token as key
        session_key = cache_key_for_session(access_token)
        session_ttl = int(access_token_expires.total_seconds())
        await cache.set(session_key, session_data, ttl=session_ttl)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds()),
            "user": user
        }
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token"""
        payload = self.verify_token(refresh_token, token_type="refresh")
        if not payload:
            return None
        
        # Create new access token
        token_data = {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "username": payload.get("username"),
            "scopes": payload.get("scopes", [])
        }
        
        access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
        new_access_token = self.create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )
        
        # Update session cache
        cache = await get_cache()
        session_data = {
            "user_id": int(payload.get("sub")),
            "email": payload.get("email"),
            "username": payload.get("username"),
            "created_at": datetime.utcnow().isoformat(),
            "refreshed_at": datetime.utcnow().isoformat()
        }
        
        session_key = cache_key_for_session(new_access_token)
        session_ttl = int(access_token_expires.total_seconds())
        await cache.set(session_key, session_data, ttl=session_ttl)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds())
        }
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke a token by removing it from cache"""
        try:
            cache = await get_cache()
            session_key = cache_key_for_session(token)
            return await cache.delete(session_key)
        except Exception as e:
            logger.error(f"Failed to revoke token: {str(e)}")
            return False
    
    async def is_token_revoked(self, token: str) -> bool:
        """Check if token is revoked (not in cache)"""
        try:
            cache = await get_cache()
            session_key = cache_key_for_session(token)
            return not await cache.exists(session_key)
        except Exception as e:
            logger.error(f"Failed to check token revocation: {str(e)}")
            return True  # Assume revoked on error
    
    async def get_session_data(self, token: str) -> Optional[Dict[str, Any]]:
        """Get session data from cache"""
        try:
            cache = await get_cache()
            session_key = cache_key_for_session(token)
            return await cache.get(session_key)
        except Exception as e:
            logger.error(f"Failed to get session data: {str(e)}")
            return None

# Global JWT manager instance
_jwt_manager: Optional[JWTManager] = None

def get_jwt_manager() -> JWTManager:
    """Get or create global JWT manager instance"""
    global _jwt_manager
    
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    
    return _jwt_manager

# Authentication exceptions
class AuthenticationError(HTTPException):
    """Authentication error"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class AuthorizationError(HTTPException):
    """Authorization error"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

class TokenExpiredError(AuthenticationError):
    """Token expired error"""
    def __init__(self):
        super().__init__(detail="Token has expired")

class InvalidTokenError(AuthenticationError):
    """Invalid token error"""
    def __init__(self):
        super().__init__(detail="Invalid token")