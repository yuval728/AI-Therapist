"""Centralized error handling utilities."""
from typing import Optional, Dict, Any, Callable, Union
from loguru import logger
from fastapi import HTTPException, status
import functools
import asyncio


class TherapyError(Exception):
    """Base exception for therapy-related errors."""
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class AuthenticationError(TherapyError):
    """Authentication-related errors."""
    pass


class ValidationError(TherapyError):
    """Input validation errors."""
    pass


class GraphExecutionError(TherapyError):
    """Therapy graph execution errors."""
    pass


class DatabaseError(TherapyError):
    """Database operation errors."""
    pass


class ExternalServiceError(TherapyError):
    """External service integration errors."""
    pass


class RateLimitError(TherapyError):
    """Rate limiting errors."""
    pass


def handle_auth_error(error: Exception) -> HTTPException:
    """Handle authentication errors consistently."""
    logger.error(f"Authentication error: {error}")
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed"
    )


def handle_validation_error(error: Exception) -> HTTPException:
    """Handle validation errors consistently."""
    logger.error(f"Validation error: {error}")
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid input data"
    )


def handle_internal_error(error: Exception) -> HTTPException:
    """Handle internal server errors consistently."""
    logger.error(f"Internal error: {error}")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error"
    )


def safe_execute(func: Callable, *args, default=None, log_error: bool = True, **kwargs) -> Any:
    """Safely execute a function with configurable error handling."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"Error executing {func.__name__}: {e}")
        return default


async def safe_execute_async(func: Callable, *args, default=None, log_error: bool = True, **kwargs) -> Any:
    """Safely execute an async function with configurable error handling."""
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"Error executing {func.__name__}: {e}")
        return default


def with_fallback(fallback_value: Any = None, log_errors: bool = True):
    """Decorator to provide fallback values for functions that might fail."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return safe_execute(func, *args, default=fallback_value, log_error=log_errors, **kwargs)
        return wrapper
    return decorator


def with_async_fallback(fallback_value: Any = None, log_errors: bool = True):
    """Decorator to provide fallback values for async functions that might fail."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await safe_execute_async(func, *args, default=fallback_value, log_error=log_errors, **kwargs)
        return wrapper
    return decorator


def create_error_response(message: str, error_code: str = "INTERNAL_ERROR", status_code: int = 500) -> Dict[str, Any]:
    """Create standardized error response dictionary."""
    return {
        "success": False,
        "error": message,
        "error_code": error_code,
        "status_code": status_code
    }


def handle_database_error(error: Exception) -> HTTPException:
    """Handle database-related errors consistently."""
    logger.error(f"Database error: {error}")
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database service temporarily unavailable"
    )


def handle_external_service_error(error: Exception, service_name: str = "external service") -> HTTPException:
    """Handle external service errors consistently."""
    logger.error(f"{service_name.title()} error: {error}")
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"{service_name.title()} temporarily unavailable"
    )
