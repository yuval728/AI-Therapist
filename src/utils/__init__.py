"""Utilities package for the AI therapist application."""
from .error_handling import (
    TherapyError,
    AuthenticationError,
    ValidationError,
    GraphExecutionError,
    handle_auth_error,
    handle_validation_error,
    handle_internal_error,
    safe_execute,
    safe_execute_async
)
from .logging_utils import (
    configure_logging,
    log_event,
    log_therapy_event,
    log_security_event,
    log_performance_metric,
    LogContext
)
from .validation import (
    validate_user_input,
    validate_email_address,
    validate_password_strength,
    sanitize_filename,
    validate_session_data,
    validate_json_structure
)
from .decorators import (
    timing_decorator,
    retry_decorator,
    validate_input_decorator,
    security_monitor_decorator,
    # AsyncContextManager,
    cache_decorator
)
from .cache_manager import (
    get_cache_manager,
    cache_get,
    cache_set,
    cache_delete,
    cached
)

__all__ = [
    # Error handling
    "TherapyError",
    "AuthenticationError",
    "ValidationError", 
    "GraphExecutionError",
    "handle_auth_error",
    "handle_validation_error",
    "handle_internal_error",
    "safe_execute",
    "safe_execute_async",
    
    # Logging
    "configure_logging",
    "log_event",
    "log_therapy_event",
    "log_security_event",
    "log_performance_metric",
    "LogContext",
    
    # Validation
    "validate_user_input",
    "validate_email_address",
    "validate_password_strength",
    "sanitize_filename",
    "validate_session_data",
    "validate_json_structure",
    
    # Decorators
    "timing_decorator",
    "retry_decorator",
    "validate_input_decorator",
    "security_monitor_decorator",
    "AsyncContextManager",
    "cache_decorator",
    
    # Cache management
    "get_cache_manager",
    "cache_get",
    "cache_set", 
    "cache_delete",
    "cached",
    
]
