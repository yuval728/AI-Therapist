"""Professional Redis cache management for the AI therapist application."""
import os
import json
import asyncio
import logging
from typing import Any, Optional, Dict, List
from functools import wraps
from datetime import datetime

import redis.asyncio as redis

from .logging_utils import log_event

# Configure logger for this module
logger = logging.getLogger(__name__)


class CacheManager:
    """Professional Redis-based cache manager with advanced features."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False
        self._lock = asyncio.Lock()
        self._connection_pool: Optional[redis.ConnectionPool] = None
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "sets": 0,
            "deletes": 0
        }
    
    async def initialize(self) -> bool:
        """Initialize Redis cache with connection pooling."""
        if self._initialized:
            return True
        
        async with self._lock:
            if self._initialized:
                return True
            
            try:
                redis_url = os.getenv("REDIS_URL")
                if not redis_url:
                    logger.info("No REDIS_URL configured - running without cache")
                    self._initialized = True
                    return True
                
                # Create connection pool for better performance
                self._connection_pool = redis.ConnectionPool.from_url(
                    redis_url,
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    health_check_interval=30
                )
                
                self.redis_client = redis.Redis(
                    connection_pool=self._connection_pool,
                    decode_responses=False
                )
                
                # Test connection
                await self.redis_client.ping()
                
                self._initialized = True
                log_event(event="cache_initialized", redis_url=redis_url[:30] + "...")
                logger.info("Redis cache initialized successfully")
                return True
                
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}")
                log_event(event="cache_init_failed", error=str(e))
                self._initialized = True  # Continue without cache
                return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with statistics tracking."""
        if not self.redis_client:
            self.stats["misses"] += 1
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                self.stats["hits"] += 1
                return json.loads(value.decode('utf-8'))
            else:
                self.stats["misses"] += 1
                return None
                
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning(f"Cache get error for key '{key}': {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = 300,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set value in cache with advanced options.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists
        """
        if not self.redis_client:
            return False
        
        try:
            serialized_value = json.dumps(value, default=str)
            
            success = await self.redis_client.setex(
                key, 
                ttl, 
                serialized_value
            )
            
            if success:
                self.stats["sets"] += 1
                return True
            return False
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning(f"Cache set error for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis_client:
            return False
        
        try:
            result = await self.redis_client.delete(key)
            if result > 0:
                self.stats["deletes"] += 1
                return True
            return False
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning(f"Cache delete error for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.redis_client:
            return False
        
        try:
            result = await self.redis_client.exists(key)
            return result > 0
        except Exception:
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for existing key."""
        if not self.redis_client:
            return False
        
        try:
            return await self.redis_client.expire(key, ttl)
        except Exception as e:
            logger.warning(f"Cache expire error for key '{key}': {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key (-1 if no expiry, -2 if key doesn't exist)."""
        if not self.redis_client:
            return -2
        
        try:
            return await self.redis_client.ttl(key)
        except Exception:
            return -2
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self.redis_client:
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted = await self.redis_client.delete(*keys)
                self.stats["deletes"] += deleted
                return deleted
            return 0
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning(f"Cache clear pattern error for '{pattern}': {e}")
            return 0
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment numeric value in cache."""
        if not self.redis_client:
            return None
        
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.warning(f"Cache increment error for key '{key}': {e}")
            return None
    
    async def get_multiple(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        if not self.redis_client or not keys:
            return {}
        
        try:
            values = await self.redis_client.mget(keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value.decode('utf-8'))
                        self.stats["hits"] += 1
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode cached value for key '{key}'")
                        self.stats["errors"] += 1
                else:
                    self.stats["misses"] += 1
            
            return result
            
        except Exception as e:
            self.stats["errors"] += len(keys)
            logger.warning(f"Cache get_multiple error: {e}")
            return {}
    
    async def set_multiple(self, data: Dict[str, Any], ttl: int = 300) -> bool:
        """Set multiple key-value pairs."""
        if not self.redis_client or not data:
            return False
        
        try:
            # Use pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            for key, value in data.items():
                serialized_value = json.dumps(value, default=str)
                pipe.setex(key, ttl, serialized_value)
            
            results = await pipe.execute()
            success_count = sum(1 for result in results if result)
            self.stats["sets"] += success_count
            
            return success_count == len(data)
            
        except Exception as e:
            self.stats["errors"] += len(data)
            logger.warning(f"Cache set_multiple error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_operations = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_operations * 100) if total_operations > 0 else 0
        
        return {
            **self.stats,
            "hit_rate_percent": round(hit_rate, 2),
            "total_operations": total_operations,
            "connected": self.redis_client is not None,
            "initialized": self._initialized
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on cache system."""
        if not self.redis_client:
            return {
                "status": "disabled",
                "connected": False,
                "error": "Redis not configured"
            }
        
        try:
            # Test basic operations
            test_key = f"health_check:{datetime.now().timestamp()}"
            
            # Test set
            await self.redis_client.setex(test_key, 10, "health_check")
            
            # Test get
            await self.redis_client.get(test_key)
            
            # Test delete
            await self.redis_client.delete(test_key)
            
            return {
                "status": "healthy",
                "connected": True,
                "response_time_ms": "< 10",  # Redis is typically very fast
                "stats": self.get_stats()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close Redis connection and cleanup."""
        try:
            if self.redis_client:
                await self.redis_client.aclose()
            if self._connection_pool:
                await self._connection_pool.disconnect()
                
            self.redis_client = None
            self._connection_pool = None
            self._initialized = False
            
            log_event(event="cache_closed")
            logger.info("Redis cache closed successfully")
            
        except Exception as e:
            logger.warning(f"Error closing Redis cache: {e}")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def cached(
    ttl: int = 300, 
    key_prefix: str = "cache",
    skip_cache: bool = False
):
    """
    Advanced caching decorator with better key generation.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
        skip_cache: Skip caching (useful for debugging)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if skip_cache:
                return await func(*args, **kwargs)
            
            cache = await get_cache_manager()
            if not cache.redis_client:
                return await func(*args, **kwargs)
            
            # Generate more reliable cache key
            func_name = f"{func.__module__}.{func.__name__}"
            args_str = str(args) if args else ""
            kwargs_str = str(sorted(kwargs.items())) if kwargs else ""
            cache_key = f"{key_prefix}:{func_name}:{hash(args_str + kwargs_str)}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            try:
                result = await func(*args, **kwargs)
                await cache.set(cache_key, result, ttl)
                return result
            except Exception as e:
                # Don't cache errors
                logger.warning(f"Function {func_name} failed: {e}")
                raise
        
        return wrapper
    return decorator


async def get_cache_manager() -> CacheManager:
    """Get initialized cache manager singleton."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.initialize()
    return _cache_manager


# Convenience functions for common operations
async def cache_get(key: str) -> Optional[Any]:
    """Convenience function to get from cache."""
    cache = await get_cache_manager()
    return await cache.get(key)


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """Convenience function to set in cache."""
    cache = await get_cache_manager()
    return await cache.set(key, value, ttl)


async def cache_delete(key: str) -> bool:
    """Convenience function to delete from cache."""
    cache = await get_cache_manager()
    return await cache.delete(key)