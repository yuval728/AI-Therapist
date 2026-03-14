"""API module for AI therapist application."""

from .routes import (
    auth_router,
    users_router,
    sessions_router,
    health_router,
    chat_router
)
from .middleware import (
    PerformanceMiddleware,
    # SecurityMiddleware,
    # AuthenticationMiddleware,
    # CORSMiddleware,
    # ErrorHandlingMiddleware,
    # get_current_user,
    # get_optional_user
)

__all__ = [
    "auth_router",
    "users_router",
    "sessions_router", 
    "health_router",
    "chat_router",
    "PerformanceMiddleware"
    # "SecurityMiddleware",
    # "AuthenticationMiddleware",
    # "CORSMiddleware",
    # "ErrorHandlingMiddleware",
    # "get_current_user",
    # "get_optional_user"
]
