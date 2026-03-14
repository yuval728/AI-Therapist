"""Centralized error handling utilities with monitoring and alerting.

Key improvements:
- Error aggregation and monitoring
- Performance tracking and alerting
- Circuit breaker pattern for resilience
- Structured error reporting
- Rate limiting on error notifications
- Health status integration
"""
import time
import asyncio
from typing import Optional, Dict, Any, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger
from fastapi import HTTPException, status
import functools
from contextvars import ContextVar

# Error tracking and monitoring
error_context: ContextVar[Dict[str, Any]] = ContextVar('error_context', default={})


@dataclass
class ErrorMetrics:
    """Track error metrics for monitoring and alerting."""
    count: int = 0
    last_error: Optional[datetime] = None
    error_types: Dict[str, int] = field(default_factory=dict)
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def record_error(self, error_type: str, error_msg: str):
        """Record an error occurrence."""
        self.count += 1
        self.last_error = datetime.utcnow()
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
        self.recent_errors.append({
            'type': error_type,
            'message': error_msg,
            'timestamp': self.last_error
        })


@dataclass
class CircuitBreakerState:
    """Circuit breaker for preventing cascade failures."""
    failure_count: int = 0
    last_failure: Optional[datetime] = None
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    
    def should_allow_request(self) -> bool:
        """Check if request should be allowed through circuit breaker."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if (datetime.utcnow() - self.last_failure).seconds > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record successful operation."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
        self.failure_count = 0
    
    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


# Global error tracking
error_metrics = ErrorMetrics()
circuit_breakers: Dict[str, CircuitBreakerState] = defaultdict(CircuitBreakerState)
alert_cooldowns: Dict[str, datetime] = {}


class TherapyError(Exception):
    """Base exception with structured error reporting."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None, severity: str = "ERROR"):
        self.message = message
        self.error_code = error_code or "THERAPY_ERROR"
        self.context = context or {}
        self.severity = severity
        self.timestamp = datetime.utcnow()
        
        # Record error metrics
        error_metrics.record_error(self.__class__.__name__, message)
        
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to structured dictionary."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context,
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat()
        }


class AuthenticationError(TherapyError):
    """Authentication-related errors."""
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, error_code="AUTH_ERROR", **kwargs)


class ValidationError(TherapyError):
    """Input validation errors."""
    def __init__(self, message: str = "Invalid input data", **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)


class GraphExecutionError(TherapyError):
    """Therapy graph execution errors."""
    def __init__(self, message: str = "Graph execution failed", **kwargs):
        super().__init__(message, error_code="GRAPH_ERROR", **kwargs)


class DatabaseError(TherapyError):
    """Database operation errors."""
    def __init__(self, message: str = "Database operation failed", **kwargs):
        super().__init__(message, error_code="DB_ERROR", **kwargs)


class ExternalServiceError(TherapyError):
    """External service integration errors."""
    def __init__(self, message: str = "External service error", **kwargs):
        super().__init__(message, error_code="SERVICE_ERROR", **kwargs)


class RateLimitError(TherapyError):
    """Rate limiting errors."""
    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(message, error_code="RATE_LIMIT_ERROR", **kwargs)


def should_send_alert(error_type: str, cooldown_minutes: int = 15) -> bool:
    """Check if an alert should be sent based on cooldown period."""
    now = datetime.utcnow()
    last_alert = alert_cooldowns.get(error_type)
    
    if last_alert is None or (now - last_alert) > timedelta(minutes=cooldown_minutes):
        alert_cooldowns[error_type] = now
        return True
    return False


async def send_error_alert(error: TherapyError, context: Optional[Dict] = None):
    """Send error alert if conditions are met."""
    if should_send_alert(error.error_code):
        alert_data = {
            **error.to_dict(),
            'context': context or error_context.get({}),
            'error_metrics': {
                'total_errors': error_metrics.count,
                'recent_error_types': dict(error_metrics.error_types)
            }
        }
        
        # Log structured alert
        logger.error("Error Alert", extra={
            'alert': True,
            'alert_data': alert_data
        })


def with_circuit_breaker(service_name: str):
    """Decorator to add circuit breaker protection."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            breaker = circuit_breakers[service_name]
            
            if not breaker.should_allow_request():
                raise ExternalServiceError(
                    f"Circuit breaker open for {service_name}",
                    context={'service': service_name, 'state': breaker.state}
                )
            
            try:
                start_time = time.time()
                result = await func(*args, **kwargs)
                
                # Record success metrics
                execution_time = time.time() - start_time
                breaker.record_success()
                
                logger.debug(f"Circuit breaker success for {service_name}", extra={
                    'service': service_name,
                    'execution_time': execution_time,
                    'circuit_state': breaker.state
                })
                
                return result
                
            except Exception as e:
                breaker.record_failure()
                
                # Convert to structured error
                if not isinstance(e, TherapyError):
                    error = ExternalServiceError(
                        f"Service {service_name} failed: {str(e)}",
                        context={'service': service_name, 'original_error': str(e)}
                    )
                else:
                    error = e
                
                await send_error_alert(error)
                raise error
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            breaker = circuit_breakers[service_name]
            
            if not breaker.should_allow_request():
                raise ExternalServiceError(
                    f"Circuit breaker open for {service_name}",
                    context={'service': service_name, 'state': breaker.state}
                )
            
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                
                execution_time = time.time() - start_time
                breaker.record_success()
                
                logger.debug(f"Circuit breaker success for {service_name}", extra={
                    'service': service_name,
                    'execution_time': execution_time,
                    'circuit_state': breaker.state
                })
                
                return result
                
            except Exception as e:
                breaker.record_failure()
                
                if not isinstance(e, TherapyError):
                    error = ExternalServiceError(
                        f"Service {service_name} failed: {str(e)}",
                        context={'service': service_name, 'original_error': str(e)}
                    )
                else:
                    error = e
                
                # Send alert (sync version)
                if should_send_alert(error.error_code):
                    logger.error("Error Alert", extra={
                        'alert': True,
                        'alert_data': error.to_dict()
                    })
                
                raise error
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator



def handle_auth_error(error: Exception) -> HTTPException:
    """Handle authentication errors with monitoring."""
    if isinstance(error, TherapyError):
        error_data = error.to_dict()
    else:
        error_data = {'message': str(error), 'type': type(error).__name__}
    
    logger.error("Authentication error", extra={
        'error_type': 'auth_error',
        'error_data': error_data,
        'context': error_context.get({})
    })
    
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed"
    )


def handle_validation_error(error: Exception) -> HTTPException:
    """Handle validation errors with monitoring."""
    if isinstance(error, TherapyError):
        error_data = error.to_dict()
    else:
        error_data = {'message': str(error), 'type': type(error).__name__}
    
    logger.error("Validation error", extra={
        'error_type': 'validation_error',
        'error_data': error_data,
        'context': error_context.get({})
    })
    
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid input data"
    )


def handle_internal_error(error: Exception) -> HTTPException:
    """Handle internal server errors with monitoring."""
    if isinstance(error, TherapyError):
        error_data = error.to_dict()
    else:
        error_data = {'message': str(error), 'type': type(error).__name__}
    
    logger.error("Internal server error", extra={
        'error_type': 'internal_error',
        'error_data': error_data,
        'context': error_context.get({}),
        'alert': True
    })
    
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error"
    )


def handle_database_error(error: Exception) -> HTTPException:
    """Handle database-related errors with circuit breaker awareness."""
    if isinstance(error, TherapyError):
        error_data = error.to_dict()
    else:
        error_data = {'message': str(error), 'type': type(error).__name__}
    
    # Check circuit breaker state
    breaker = circuit_breakers.get('database', CircuitBreakerState())
    
    logger.error("Database error", extra={
        'error_type': 'database_error',
        'error_data': error_data,
        'circuit_state': breaker.state,
        'context': error_context.get({}),
        'alert': breaker.state == "OPEN"
    })
    
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database service temporarily unavailable"
    )


def handle_external_service_error(error: Exception, service_name: str = "external service") -> HTTPException:
    """Handle external service errors with circuit breaker awareness."""
    if isinstance(error, TherapyError):
        error_data = error.to_dict()
    else:
        error_data = {'message': str(error), 'type': type(error).__name__}
    
    breaker = circuit_breakers.get(service_name, CircuitBreakerState())
    
    logger.error(f"{service_name.title()} error", extra={
        'error_type': 'external_service_error',
        'service_name': service_name,
        'error_data': error_data,
        'circuit_state': breaker.state,
        'context': error_context.get({}),
        'alert': breaker.state == "OPEN"
    })
    
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"{service_name.title()} temporarily unavailable"
    )


async def safe_execute_async(func: Callable, *args, default=None, 
                           log_error: bool = True, service_name: Optional[str] = None, **kwargs) -> Any:
    """Safely execute an async function with enhanced error handling."""
    start_time = time.time()
    
    try:
        result = await func(*args, **kwargs)
        
        # Log successful execution
        execution_time = time.time() - start_time
        if service_name and execution_time > 1.0:  # Log slow operations
            logger.warning("Slow operation detected", extra={
                'function': func.__name__,
                'service': service_name,
                'execution_time': execution_time,
                'context': error_context.get({})
            })
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        
        if log_error:
            error_data = e.to_dict() if isinstance(e, TherapyError) else {
                'message': str(e), 'type': type(e).__name__
            }
            
            logger.error(f"Error executing {func.__name__}", extra={
                'function': func.__name__,
                'service': service_name,
                'execution_time': execution_time,
                'error_data': error_data,
                'context': error_context.get({}),
                'alert': isinstance(e, (DatabaseError, ExternalServiceError))
            })
        
        return default


def safe_execute(func: Callable, *args, default=None, 
                log_error: bool = True, service_name: Optional[str] = None, **kwargs) -> Any:
    """Safely execute a function with enhanced error handling."""
    start_time = time.time()
    
    try:
        result = func(*args, **kwargs)
        
        execution_time = time.time() - start_time
        if service_name and execution_time > 1.0:
            logger.warning("Slow operation detected", extra={
                'function': func.__name__,
                'service': service_name,
                'execution_time': execution_time,
                'context': error_context.get({})
            })
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        
        if log_error:
            error_data = e.to_dict() if isinstance(e, TherapyError) else {
                'message': str(e), 'type': type(e).__name__
            }
            
            logger.error(f"Error executing {func.__name__}", extra={
                'function': func.__name__,
                'service': service_name,
                'execution_time': execution_time,
                'error_data': error_data,
                'context': error_context.get({}),
                'alert': isinstance(e, (DatabaseError, ExternalServiceError))
            })
        
        return default


def with_error_monitoring(service_name: Optional[str] = None, log_errors: bool = True):
    """Enhanced decorator with error monitoring and performance tracking."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await safe_execute_async(
                func, *args, log_error=log_errors, 
                service_name=service_name, **kwargs
            )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return safe_execute(
                func, *args, log_error=log_errors,
                service_name=service_name, **kwargs
            )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def create_error_response(message: str, error_code: str = "INTERNAL_ERROR", 
                         status_code: int = 500, context: Optional[Dict] = None) -> Dict[str, Any]:
    """Create standardized error response with enhanced context."""
    response = {
        "success": False,
        "error": message,
        "error_code": error_code,
        "status_code": status_code,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if context:
        response["context"] = context
    
    return response


def get_error_metrics() -> Dict[str, Any]:
    """Get current error metrics for monitoring dashboards."""
    return {
        'total_errors': error_metrics.count,
        'last_error': error_metrics.last_error.isoformat() if error_metrics.last_error else None,
        'error_types': dict(error_metrics.error_types),
        'recent_errors': list(error_metrics.recent_errors)[-10:],  # Last 10 errors
        'circuit_breakers': {
            name: {
                'state': breaker.state,
                'failure_count': breaker.failure_count,
                'last_failure': breaker.last_failure.isoformat() if breaker.last_failure else None
            }
            for name, breaker in circuit_breakers.items()
        }
    }


def reset_error_metrics():
    """Reset error metrics (useful for testing)."""
    global error_metrics, circuit_breakers, alert_cooldowns
    error_metrics = ErrorMetrics()
    circuit_breakers.clear()
    alert_cooldowns.clear()


# Legacy compatibility functions (kept for backward compatibility)
def with_fallback(fallback_value: Any = None, log_errors: bool = True):
    """Legacy decorator - use with_error_monitoring instead."""
    return with_error_monitoring(log_errors=log_errors)


def with_async_fallback(fallback_value: Any = None, log_errors: bool = True):
    """Legacy decorator - use with_error_monitoring instead.""" 
    return with_error_monitoring(log_errors=log_errors)
