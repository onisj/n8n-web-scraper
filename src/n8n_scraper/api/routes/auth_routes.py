"""
Authentication routes for the n8n AI Knowledge System
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import (
    UserCreate, UserLogin, UserResponse, UserUpdate, 
    PasswordChange, Token, TokenData, RefreshTokenRequest
)
from ...database.user_service import UserService, get_user_service
from ...auth.jwt_auth import get_jwt_manager, AuthenticationError, InvalidTokenError
from ...cache.redis_cache import get_cache, cache_key_for_user
from ...database.connection import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)

# Dependency to get current user
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service)
) -> UserResponse:
    """Get current authenticated user"""
    if not credentials:
        raise AuthenticationError("Missing authentication token")
    
    jwt_manager = get_jwt_manager()
    
    # Verify token
    token_data = jwt_manager.extract_token_data(credentials.credentials)
    if not token_data or not token_data.user_id:
        raise InvalidTokenError()
    
    # Check if token is revoked
    if await jwt_manager.is_token_revoked(credentials.credentials):
        raise AuthenticationError("Token has been revoked")
    
    # Get user from database
    user = await user_service.get_user_by_id(int(token_data.user_id))
    if not user:
        raise AuthenticationError("User not found")
    
    if not user.is_active:
        raise AuthenticationError("User account is inactive")
    
    return user

# Optional dependency for routes that work with or without authentication
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service)
) -> Optional[UserResponse]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db, user_service)
    except HTTPException:
        return None

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service)
):
    """Register a new user"""
    try:
        # Create user
        user = await user_service.create_user(user_data)
        
        # Create tokens
        jwt_manager = get_jwt_manager()
        tokens = await jwt_manager.create_user_tokens(user, remember_me=False)
        
        # Log registration
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"New user registered: {user.email} from {client_ip}")
        
        return tokens
        
    except ValueError as e:
        logger.warning(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service)
):
    """Authenticate user and return tokens"""
    try:
        # Authenticate user
        user = await user_service.authenticate_user(login_data)
        if not user:
            logger.warning(f"Login failed for email: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Create tokens
        jwt_manager = get_jwt_manager()
        tokens = await jwt_manager.create_user_tokens(user, remember_me=login_data.remember_me)
        
        # Log successful login
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"User logged in: {user.email} from {client_ip}")
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/logout", response_model=None)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: UserResponse = Depends(get_current_user)
):
    """Logout user and revoke token"""
    try:
        jwt_manager = get_jwt_manager()
        await jwt_manager.revoke_token(credentials.credentials)
        
        logger.info(f"User logged out: {current_user.email}")
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Refresh access token using refresh token"""
    try:
        jwt_manager = get_jwt_manager()
        tokens = await jwt_manager.refresh_access_token(request.refresh_token)
        
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service)
):
    """Update current user profile"""
    try:
        updated_user = await user_service.update_user(current_user.id, user_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        logger.info(f"User profile updated: {current_user.email}")
        return updated_user
        
    except ValueError as e:
        logger.warning(f"Profile update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )

@router.post("/change-password", response_model=None)
async def change_password(
    password_data: PasswordChange,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service)
):
    """Change user password"""
    try:
        success = await user_service.change_password(current_user.id, password_data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password"
            )
        
        logger.info(f"Password changed for user: {current_user.email}")
        return {"message": "Password changed successfully"}
        
    except ValueError as e:
        logger.warning(f"Password change failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

@router.post("/deactivate", response_model=None)
async def deactivate_account(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service)
):
    """Deactivate current user account"""
    try:
        success = await user_service.deactivate_user(current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to deactivate account"
            )
        
        logger.info(f"Account deactivated: {current_user.email}")
        return {"message": "Account deactivated successfully"}
        
    except Exception as e:
        logger.error(f"Account deactivation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account deactivation failed"
        )

@router.get("/session", response_model=None)
async def get_session_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get current session information"""
    try:
        jwt_manager = get_jwt_manager()
        session_data = await jwt_manager.get_session_data(credentials.credentials)
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return {
            "user": current_user,
            "session": session_data,
            "token_valid": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session info error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session info"
        )

@router.get("/verify-token", response_model=None)
async def verify_token(
    current_user: UserResponse = Depends(get_current_user)
):
    """Verify if current token is valid"""
    return {
        "valid": True,
        "user": current_user,
        "timestamp": datetime.utcnow().isoformat()
    }