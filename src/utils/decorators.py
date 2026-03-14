"""Utility decorators for the AI therapist application."""
import time
import asyncio
from functools import wraps
from typing import Any, Callable, Optional, Union
from .logging_utils import log_performance_metric, log_security_event
from .error_handling import safe_execute, safe_execute_async


def timing_decorator(operation_name: Optional[str] = None):
    """Decorator to measure and log execution time."""
    def decorator(func: Callable) -> Callable:
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
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def retry_decorator(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry failed operations with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def rate_limit_decorator(calls_per_minute: int = 60):
    """Decorator to implement rate limiting."""
    call_times = []
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # Remove calls older than 1 minute
            call_times[:] = [t for t in call_times if now - t < 60]
            
            if len(call_times) >= calls_per_minute:
                raise Exception(f"Rate limit exceeded: {calls_per_minute} calls per minute")
            
            call_times.append(now)
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_input_decorator(validator_func: Callable):
    """Decorator to validate function inputs."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate inputs using the provided validator
            validation_result = validator_func(*args, **kwargs)
            if not validation_result.get("is_valid", True):
                errors = validation_result.get("errors", ["Validation failed"])
                raise ValueError(f"Input validation failed: {', '.join(errors)}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def security_monitor_decorator(monitor_pii: bool = True, monitor_injection: bool = True):
    """Decorator to monitor for security issues in function inputs."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Basic security monitoring
            for arg in args:
                if isinstance(arg, str):
                    if monitor_injection and _detect_injection_attempt(arg):
                        log_security_event(
                            event="injection_attempt_detected",
                            attack_type="prompt_injection",
                            severity="HIGH"
                        )
                        raise ValueError("Potential injection attempt detected")
                    
                    if monitor_pii and _detect_pii(arg):
                        log_security_event(
                            event="pii_detected",
                            attack_type="pii_exposure",
                            severity="MEDIUM"
                        )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _detect_injection_attempt(text: str) -> bool:
    """Basic injection detection patterns."""
    injection_patterns = [
        r'ignore\s+previous\s+instructions',
        r'system\s*:',
        r'assistant\s*:',
        r'<\|.*?\|>',
        r'```.*?system.*?```',
    ]
    
    import re
    for pattern in injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _detect_pii(text: str) -> bool:
    """Basic PII detection patterns."""
    pii_patterns = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b',  # Phone number
    ]
    
    import re
    for pattern in pii_patterns:
        if re.search(pattern, text):
            return True
    return False


class AsyncContextManager:
    """Async context manager for resource management."""
    
    def __init__(self, setup_func: Callable, cleanup_func: Callable):
        self.setup_func = setup_func
        self.cleanup_func = cleanup_func
        self.resource = None
    
    async def __aenter__(self):
        self.resource = await self.setup_func()
        return self.resource
    
    async def __aaxit__(self, exc_type, exc_val, exc_tb):
        if self.cleanup_func and self.resource:
            await self.cleanup_func(self.resource)


def cache_decorator(ttl_seconds: int = 300):
    """Simple in-memory cache decorator with TTL."""
    cache = {}
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            now = time.time()
            
            # Check if cached result exists and is still valid
            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < ttl_seconds:
                    return result
                else:
                    del cache[key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[key] = (result, now)
            return result
        
        return wrapper
    return decorator
