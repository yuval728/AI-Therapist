"""Centralized error handling utilities."""
from typing import Optional, Dict, Any
from loguru import logger
from fastapi import HTTPException, status


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


def safe_execute(func, *args, **kwargs) -> Optional[Any]:
    """Safely execute a function with error logging."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing {func.__name__}: {e}")
        return None


async def safe_execute_async(func, *args, **kwargs) -> Optional[Any]:
    """Safely execute an async function with error logging."""
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing {func.__name__}: {e}")
        return None
