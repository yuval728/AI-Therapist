"""Simple rate limiting utilities for API endpoints."""
import time
import asyncio
from typing import Dict
from collections import defaultdict, deque


class SimpleRateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self._windows: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(self, key: str, limit: int, window: int = 60) -> bool:
        """Check if request is within rate limit."""
        async with self._lock:
            now = time.time()
            window_start = now - window
            
            # Get window for this key
            request_times = self._windows[key]
            
            # Remove old requests
            while request_times and request_times[0] < window_start:
                request_times.popleft()
            
            # Check limit
            if len(request_times) >= limit:
                return False
            
            # Add current request
            request_times.append(now)
            return True


# Global rate limiter instance
rate_limiter = SimpleRateLimiter()


