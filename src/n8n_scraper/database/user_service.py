"""User database service for the n8n AI Knowledge System"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.exc import IntegrityError
from email_validator import validate_email, EmailNotValidError

from ..api.models.user import (
    User, UserSession, UserCreate, UserLogin, UserUpdate, 
    PasswordChange, UserResponse
)
from ..auth.jwt_auth import get_jwt_manager
from ..cache.redis_cache import get_cache, cache_key_for_user

logger = logging.getLogger(__name__)

class UserService:
    """Service for user management operations"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.jwt_manager = get_jwt_manager()
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user"""
        # Validate passwords match
        user_data.validate_passwords_match()
        
        # Validate email format
        try:
            validate_email(user_data.email)
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email format: {str(e)}")
        
        # Check if user already exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        existing_username = await self.get_user_by_username(user_data.username)
        if existing_username:
            raise ValueError("User with this username already exists")
        
        try:
            # Create user
            hashed_password = User.get_password_hash(user_data.password)
            
            db_user = User(
                email=user_data.email.lower(),
                username=user_data.username,
                hashed_password=hashed_password,
                full_name=user_data.full_name,
                is_active=True,
                is_superuser=False
            )
            
            self.db.add(db_user)
            await self.db.commit()
            await self.db.refresh(db_user)
            
            logger.info(f"Created new user: {user_data.email}")
            
            # Clear user cache
            await self._clear_user_cache(db_user.id)
            
            return UserResponse.model_validate(db_user)
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database integrity error creating user: {str(e)}")
            raise ValueError("User with this email or username already exists")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user: {str(e)}")
            raise ValueError(f"Failed to create user: {str(e)}")
    
    async def authenticate_user(self, login_data: UserLogin) -> Optional[UserResponse]:
        """Authenticate user with email and password"""
        try:
            # Get user by email
            user = await self.get_user_by_email(login_data.email)
            if not user:
                logger.warning(f"Authentication failed: User not found for email {login_data.email}")
                return None
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Authentication failed: User {login_data.email} is inactive")
                return None
            
            # Get full user from database
            stmt = select(User).where(User.email == login_data.email.lower())
            result = await self.db.execute(stmt)
            db_user = result.scalar_one_or_none()
            
            if not db_user:
                return None
            
            # Verify password
            if not db_user.verify_password(login_data.password):
                logger.warning(f"Authentication failed: Invalid password for {login_data.email}")
                return None
            
            # Update last login
            db_user.last_login = datetime.utcnow()
            await self.db.commit()
            
            logger.info(f"User authenticated successfully: {login_data.email}")
            
            # Clear user cache
            await self._clear_user_cache(db_user.id)
            
            return UserResponse.model_validate(db_user)
            
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[UserResponse]:
        """Get user by ID with caching"""
        # Try cache first
        cache = await get_cache()
        cache_key = cache_key_for_user(user_id, "profile")
        cached_user = await cache.get(cache_key)
        
        if cached_user:
            logger.debug(f"Cache hit for user {user_id}")
            return UserResponse.model_validate(cached_user)
        
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                user_response = UserResponse.model_validate(user)
                # Cache for 1 hour
                await cache.set(cache_key, user_response.model_dump(), ttl=3600)
                return user_response
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Get user by email"""
        try:
            stmt = select(User).where(User.email == email.lower())
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                return UserResponse.model_validate(user)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        """Get user by username"""
        try:
            stmt = select(User).where(User.username == username)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                return UserResponse.model_validate(user)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {str(e)}")
            return None
    
    async def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[UserResponse]:
        """Update user information"""
        try:
            # Get existing user
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Update fields
            update_data = user_data.model_dump(exclude_unset=True)
            
            if update_data:
                # Check for email/username conflicts
                if 'email' in update_data:
                    existing_email = await self.get_user_by_email(update_data['email'])
                    if existing_email and existing_email.id != user_id:
                        raise ValueError("Email already in use by another user")
                    update_data['email'] = update_data['email'].lower()
                
                if 'username' in update_data:
                    existing_username = await self.get_user_by_username(update_data['username'])
                    if existing_username and existing_username.id != user_id:
                        raise ValueError("Username already in use by another user")
                
                # Update user
                for field, value in update_data.items():
                    setattr(user, field, value)
                
                user.updated_at = datetime.utcnow()
                await self.db.commit()
                await self.db.refresh(user)
                
                logger.info(f"Updated user {user_id}")
                
                # Clear user cache
                await self._clear_user_cache(user_id)
                
                return UserResponse.model_validate(user)
            
            return UserResponse.model_validate(user)
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database integrity error updating user: {str(e)}")
            raise ValueError("Email or username already in use")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating user {user_id}: {str(e)}")
            raise ValueError(f"Failed to update user: {str(e)}")
    
    async def change_password(self, user_id: int, password_data: PasswordChange) -> bool:
        """Change user password"""
        # Validate passwords match
        password_data.validate_passwords_match()
        
        try:
            # Get user
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Verify current password
            if not user.verify_password(password_data.current_password):
                raise ValueError("Current password is incorrect")
            
            # Update password
            user.hashed_password = User.get_password_hash(password_data.new_password)
            user.updated_at = datetime.utcnow()
            
            await self.db.commit()
            
            logger.info(f"Password changed for user {user_id}")
            
            # Clear user cache and revoke all sessions
            await self._clear_user_cache(user_id)
            await self._revoke_all_user_sessions(user_id)
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error changing password for user {user_id}: {str(e)}")
            raise ValueError(f"Failed to change password: {str(e)}")
    
    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user account"""
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            user.is_active = False
            user.updated_at = datetime.utcnow()
            
            await self.db.commit()
            
            logger.info(f"Deactivated user {user_id}")
            
            # Clear user cache and revoke all sessions
            await self._clear_user_cache(user_id)
            await self._revoke_all_user_sessions(user_id)
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deactivating user {user_id}: {str(e)}")
            return False
    
    async def get_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """Get list of users with pagination"""
        try:
            stmt = select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
            result = await self.db.execute(stmt)
            users = result.scalars().all()
            
            return [UserResponse.model_validate(user) for user in users]
            
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            return []
    
    async def search_users(self, query: str, limit: int = 50) -> List[UserResponse]:
        """Search users by email, username, or full name"""
        try:
            search_term = f"%{query.lower()}%"
            stmt = select(User).where(
                or_(
                    User.email.ilike(search_term),
                    User.username.ilike(search_term),
                    User.full_name.ilike(search_term)
                )
            ).limit(limit).order_by(User.created_at.desc())
            
            result = await self.db.execute(stmt)
            users = result.scalars().all()
            
            return [UserResponse.model_validate(user) for user in users]
            
        except Exception as e:
            logger.error(f"Error searching users: {str(e)}")
            return []
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            # Total users
            total_stmt = select(User.id)
            total_result = await self.db.execute(total_stmt)
            total_users = len(total_result.scalars().all())
            
            # Active users
            active_stmt = select(User.id).where(User.is_active == True)
            active_result = await self.db.execute(active_stmt)
            active_users = len(active_result.scalars().all())
            
            # Recent users (last 30 days)
            from datetime import timedelta
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_stmt = select(User.id).where(User.created_at >= thirty_days_ago)
            recent_result = await self.db.execute(recent_stmt)
            recent_users = len(recent_result.scalars().all())
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "recent_users": recent_users
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return {
                "total_users": 0,
                "active_users": 0,
                "inactive_users": 0,
                "recent_users": 0
            }
    
    async def _clear_user_cache(self, user_id: int):
        """Clear all cached data for a user"""
        try:
            cache = await get_cache()
            await cache.clear_pattern(f"user:{user_id}:*")
            logger.debug(f"Cleared cache for user {user_id}")
        except Exception as e:
            logger.error(f"Error clearing cache for user {user_id}: {str(e)}")
    
    async def _revoke_all_user_sessions(self, user_id: int):
        """Revoke all active sessions for a user"""
        try:
            cache = await get_cache()
            await cache.clear_pattern(f"session:*")
            logger.debug(f"Revoked all sessions for user {user_id}")
        except Exception as e:
            logger.error(f"Error revoking sessions for user {user_id}: {str(e)}")

# Database dependency
async def get_user_service(db):
    """Get user service instance"""
    return UserService(db)