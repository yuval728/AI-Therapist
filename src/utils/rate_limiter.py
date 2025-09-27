"""Simple and efficient rate limiting utilities with Redis support."""
import time
from typing import Dict, Optional
from collections import deque
from dataclasses import dataclass

from src.utils.cache_manager import get_cache_manager
from src.utils.logging_utils import log_event


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_window: int
    window_seconds: int = 60
    
    
@dataclass
class RateLimitResult:
    """Rate limit check result."""
    allowed: bool
    remaining: int = 0
    reset_time: float = 0.0
    retry_after: Optional[float] = None


class RateLimiter:
    """Simple and efficient rate limiter with Redis support and memory fallback."""
    
    def __init__(self):
        self._memory_windows: Dict[str, deque] = {}
        self._cache_manager = None
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    async def _get_cache_manager(self):
        """Get cache manager instance."""
        if self._cache_manager is None:
            try:
                self._cache_manager = await get_cache_manager()
            except Exception as e:
                log_event(event="cache_manager_error", error=str(e))
                self._cache_manager = None
        return self._cache_manager
    
    async def check_rate_limit(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Check if request is within rate limit."""
        # cache_manager = await self._get_cache_manager()
        
        # # Try Redis first, fallback to memory
        # if cache_manager and cache_manager.redis_client:
        #     try:
        #         return await self._check_redis(key, config, cache_manager)
        #     except Exception as e:
        #         log_event(event="redis_rate_limit_error", key=key, error=str(e))
        
        return await self._check_memory(key, config)
    
    async def _check_redis(self, key: str, config: RateLimitConfig, cache_manager) -> RateLimitResult:
        """Check rate limit using Redis with simple sliding window."""
        now = time.time()
        window_start = now - config.window_seconds
        redis_key = f"rate_limit:{key}"
        
        pipe = cache_manager.redis_client.pipeline()
        
        # Remove old entries and count current requests
        pipe.zremrangebyscore(redis_key, 0, window_start)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {str(now): now})
        pipe.expire(redis_key, config.window_seconds + 1)
        
        results = await pipe.execute()
        current_count = results[1]
        
        if current_count < config.requests_per_window:
            return RateLimitResult(
                allowed=True,
                remaining=config.requests_per_window - current_count - 1,
                reset_time=now + config.window_seconds
            )
        else:
            # Remove the request we just added since it's not allowed
            await cache_manager.redis_client.zrem(redis_key, str(now))
            
            # Calculate retry_after from oldest request
            oldest = await cache_manager.redis_client.zrange(redis_key, 0, 0, withscores=True)
            retry_after = oldest[0][1] + config.window_seconds - now if oldest else config.window_seconds
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=now + config.window_seconds,
                retry_after=max(0, retry_after)
            )
    
    async def _check_memory(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Check rate limit using memory-based sliding window."""
        now = time.time()
        
        # Periodic cleanup to prevent memory leaks
        if now - self._last_cleanup > self._cleanup_interval:
            await self._cleanup_memory()
            self._last_cleanup = now
        
        # Get or create window for this key
        if key not in self._memory_windows:
            self._memory_windows[key] = deque()
        
        window = self._memory_windows[key]
        window_start = now - config.window_seconds
        
        # Remove old requests
        while window and window[0] < window_start:
            window.popleft()
        
        # Check limit
        if len(window) < config.requests_per_window:
            window.append(now)
            return RateLimitResult(
                allowed=True,
                remaining=config.requests_per_window - len(window),
                reset_time=now + config.window_seconds
            )
        else:
            retry_after = window[0] + config.window_seconds - now
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=now + config.window_seconds,
                retry_after=max(0, retry_after)
            )
    
    async def _cleanup_memory(self):
        """Clean up old memory windows to prevent memory leaks."""
        now = time.time()
        keys_to_remove = []
        
        for key, window in self._memory_windows.items():
            # Remove old entries
            while window and window[0] < now - 3600:  # Remove entries older than 1 hour
                window.popleft()
            
            # Remove empty windows
            if not window:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._memory_windows[key]

# Global rate limiter instance
rate_limiter = RateLimiter()


# Predefined rate limit configurations
RATE_LIMITS = {
    "api_general": RateLimitConfig(requests_per_window=100, window_seconds=60),
    "api_auth": RateLimitConfig(requests_per_window=10, window_seconds=60),
    "websocket_messages": RateLimitConfig(requests_per_window=50, window_seconds=60),
    "api_strict": RateLimitConfig(requests_per_window=20, window_seconds=60),
    "global_requests": RateLimitConfig(requests_per_window=1000, window_seconds=60),  # Global rate limit
    "api_messages": RateLimitConfig(requests_per_window=30, window_seconds=60),  # For chat messages
}


async def check_rate_limit(key: str, limit_type: str = "api_general") -> RateLimitResult:
    """Convenience function to check rate limits."""
    config = RATE_LIMITS.get(limit_type)
    if not config:
        raise ValueError(f"Unknown rate limit type: {limit_type}")
    
    return await rate_limiter.check_rate_limit(key, config)


