"""Redis caching utilities for the n8n AI Knowledge System"""

import json
import pickle
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Union
from functools import wraps
import redis.asyncio as redis
from redis.asyncio import Redis
import os
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class CacheConfig:
    """Redis cache configuration"""
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_password = os.getenv("REDIS_PASSWORD", "")
        self.default_ttl = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
        self.key_prefix = os.getenv("CACHE_KEY_PREFIX", "n8n_ai:")

class RedisCache:
    """Redis cache manager with async support"""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._redis: Optional[Redis] = None
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to Redis"""
        try:
            self._redis = redis.from_url(
                self.config.redis_url,
                password=self.config.redis_password or None,
                max_connections=self.config.max_connections,
                decode_responses=False  # We'll handle encoding ourselves
            )
            
            # Test connection
            await self._redis.ping()
            self._connected = True
            logger.info("Successfully connected to Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Disconnected from Redis")
    
    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key"""
        return f"{self.config.key_prefix}{key}"
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value).encode('utf-8')
        elif isinstance(value, BaseModel):
            return value.model_dump_json().encode('utf-8')
        elif isinstance(value, (dict, list)):
            return json.dumps(value).encode('utf-8')
        else:
            # Use pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize_value(self, value: bytes, value_type: str = 'auto') -> Any:
        """Deserialize value from storage"""
        try:
            if value_type == 'json' or value_type == 'auto':
                try:
                    return json.loads(value.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    if value_type == 'json':
                        raise
            
            # Try pickle if JSON fails or if explicitly requested
            return pickle.loads(value)
        except Exception as e:
            logger.error(f"Failed to deserialize cached value: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache"""
        if not self._connected or not self._redis:
            return False
        
        try:
            cache_key = self._make_key(key)
            serialized_value = self._serialize_value(value)
            ttl = ttl or self.config.default_ttl
            
            await self._redis.setex(cache_key, ttl, serialized_value)
            logger.debug(f"Cached value for key: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache for key {key}: {str(e)}")
            return False
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache"""
        if not self._connected or not self._redis:
            return default
        
        try:
            cache_key = self._make_key(key)
            value = await self._redis.get(cache_key)
            
            if value is None:
                logger.debug(f"Cache miss for key: {key}")
                return default
            
            logger.debug(f"Cache hit for key: {key}")
            return self._deserialize_value(value)
            
        except Exception as e:
            logger.error(f"Failed to get cache for key {key}: {str(e)}")
            return default
    
    async def delete(self, key: str) -> bool:
        """Delete a value from cache"""
        if not self._connected or not self._redis:
            return False
        
        try:
            cache_key = self._make_key(key)
            result = await self._redis.delete(cache_key)
            logger.debug(f"Deleted cache key: {key}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to delete cache for key {key}: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache"""
        if not self._connected or not self._redis:
            return False
        
        try:
            cache_key = self._make_key(key)
            result = await self._redis.exists(cache_key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to check existence for key {key}: {str(e)}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for a key"""
        if not self._connected or not self._redis:
            return False
        
        try:
            cache_key = self._make_key(key)
            result = await self._redis.expire(cache_key, ttl)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to set expiration for key {key}: {str(e)}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern"""
        if not self._connected or not self._redis:
            return 0
        
        try:
            cache_pattern = self._make_key(pattern)
            keys = await self._redis.keys(cache_pattern)
            
            if keys:
                result = await self._redis.delete(*keys)
                logger.info(f"Cleared {result} keys matching pattern: {pattern}")
                return result
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to clear pattern {pattern}: {str(e)}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._connected or not self._redis:
            return {"connected": False}
        
        try:
            info = await self._redis.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "Unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {"connected": False, "error": str(e)}

# Global cache instance
_cache_instance: Optional[RedisCache] = None

async def get_cache() -> RedisCache:
    """Get or create global cache instance"""
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = RedisCache()
        await _cache_instance.connect()
    
    return _cache_instance

def cache_key_for_user(user_id: int, key: str) -> str:
    """Generate cache key for user-specific data"""
    return f"user:{user_id}:{key}"

def cache_key_for_query(query: str, user_id: Optional[int] = None) -> str:
    """Generate cache key for query results"""
    import hashlib
    query_hash = hashlib.md5(query.encode()).hexdigest()[:12]
    if user_id:
        return f"query:user:{user_id}:{query_hash}"
    return f"query:global:{query_hash}"

def cache_key_for_session(session_token: str) -> str:
    """Generate cache key for user session"""
    return f"session:{session_token}"

# Decorator for caching function results
def cached(ttl: int = 3600, key_func: Optional[callable] = None):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = await get_cache()
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                import hashlib
                key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                cache_key = f"func:{hashlib.md5(key_data.encode()).hexdigest()[:12]}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for function {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            logger.debug(f"Cached result for function {func.__name__}")
            
            return result
        
        return wrapper
    return decorator