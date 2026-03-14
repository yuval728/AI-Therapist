"""Simple and efficient utility decorators for the AI therapist application."""
import time
import asyncio
import re
import random
from functools import wraps
from typing import Callable, Optional, Dict, Any

from .logging_utils import log_performance_metric, log_security_event


# Compile regex patterns once for better performance
INJECTION_PATTERNS = re.compile(
    r'ignore\s+previous\s+instructions|system\s*:|assistant\s*:|<\|.*?\|>|```.*?system.*?```',
    re.IGNORECASE
)

PII_PATTERNS = re.compile(
    r'\b\d{3}-\d{2}-\d{4}\b|'  # SSN
    r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b|'  # Credit card
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b|'  # Email
    r'\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b'  # Phone number
)


def timing_decorator(operation_name: Optional[str] = None):
    """Decorator to measure and log execution time for both sync and async functions."""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration_ms = int((time.time() - start_time) * 1000)
                    log_performance_metric(
                        operation=operation_name or func.__name__,
                        duration_ms=duration_ms,
                        success=True
                    )
                    return result
                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    log_performance_metric(
                        operation=operation_name or func.__name__,
                        duration_ms=duration_ms,
                        success=False,
                        error=str(e)
                    )
                    raise
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = int((time.time() - start_time) * 1000)
                    log_performance_metric(
                        operation=operation_name or func.__name__,
                        duration_ms=duration_ms,
                        success=True
                    )
                    return result
                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    log_performance_metric(
                        operation=operation_name or func.__name__,
                        duration_ms=duration_ms,
                        success=False,
                        error=str(e)
                    )
                    raise
            return sync_wrapper
    return decorator


def retry_decorator(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0, jitter: bool = True):
    """Decorator to retry failed operations with exponential backoff and optional jitter."""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                current_delay = delay
                for attempt in range(max_retries):
                    try:
                        return await func(*args, **kwargs)
                    except Exception:
                        if attempt == max_retries - 1:
                            raise
                        
                        # Add jitter to prevent thundering herd
                        actual_delay = current_delay
                        if jitter:
                            actual_delay *= (0.5 + random.random() * 0.5)
                        
                        await asyncio.sleep(actual_delay)
                        current_delay *= backoff
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                current_delay = delay
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception:
                        if attempt == max_retries - 1:
                            raise
                        
                        # Add jitter to prevent thundering herd
                        actual_delay = current_delay
                        if jitter:
                            actual_delay *= (0.5 + random.random() * 0.5)
                        
                        time.sleep(actual_delay)
                        current_delay *= backoff
            return sync_wrapper
    return decorator


def validate_input_decorator(validator_func: Callable):
    """Decorator to validate function inputs."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            validation_result = validator_func(*args, **kwargs)
            if not validation_result.get("is_valid", True):
                errors = validation_result.get("errors", ["Validation failed"])
                raise ValueError(f"Input validation failed: {', '.join(errors)}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def security_monitor_decorator(monitor_pii: bool = True, monitor_injection: bool = True):
    """Decorator to monitor for security issues in function inputs using pre-compiled patterns."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for arg in args:
                if isinstance(arg, str):
                    if monitor_injection and INJECTION_PATTERNS.search(arg):
                        log_security_event(
                            event="injection_attempt_detected",
                            attack_type="prompt_injection",
                            severity="HIGH"
                        )
                        raise ValueError("Potential injection attempt detected")
                    
                    if monitor_pii and PII_PATTERNS.search(arg):
                        log_security_event(
                            event="pii_detected",
                            attack_type="pii_exposure",
                            severity="MEDIUM"
                        )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


class LRUCache:
    """Simple LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 128, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, tuple] = {}
        self.access_order: Dict[str, float] = {}
    
    def get(self, key: str) -> Any:
        """Get value from cache if valid."""
        if key not in self.cache:
            return None
        
        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            del self.cache[key]
            del self.access_order[key]
            return None
        
        # Update access time
        self.access_order[key] = time.time()
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache with LRU eviction."""
        now = time.time()
        
        # Remove oldest entries if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = min(self.access_order.keys(), key=lambda k: self.access_order[k])
            del self.cache[oldest_key]
            del self.access_order[oldest_key]
        
        self.cache[key] = (value, now)
        self.access_order[key] = now


def cache_decorator(max_size: int = 128, ttl_seconds: int = 300):
    """Efficient cache decorator with LRU eviction and TTL."""
    cache = LRUCache(max_size, ttl_seconds)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        
        return wrapper
    return decorator

