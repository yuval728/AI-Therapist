"""Optimized API middleware for security, logging, rate limiting, and performance."""
from typing import Callable, Optional, Any
import time
import uuid
import asyncio
import logging
from fastapi import Request, Response, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.services import get_auth_service
from src.utils.rate_limiter import check_rate_limit
from src.config import get_settings

# Configure logger for this module
logger = logging.getLogger(__name__)

class PerformanceMiddleware(BaseHTTPMiddleware):
    """High-performance middleware with optimized caching, rate limiting, and metrics."""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = set(exclude_paths or [
            "/docs", "/redoc", "/openapi.json", "/health", "/api/health",
            "/api/health/detailed", "/api/health/metrics", "/api/health/readiness",
            "/api/health/liveness", "/favicon.ico"
        ])
        self.settings = get_settings()
        self._cache = {}  # Simple in-memory cache for frequently accessed data
        self._cache_ttl = 300  # 5 minutes
        
    def _is_excluded_path(self, path: str) -> bool:
        """Efficient path exclusion check."""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if valid."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if (time.time() - timestamp) < self._cache_ttl:
                return data
            del self._cache[key]  # Remove expired entry
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Set value in cache with timestamp."""
        self._cache[key] = (data, time.time())
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with optimized performance."""
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]  # Shorter ID for better performance
        request.state.request_id = request_id
        
        try:
            # Fast path for excluded routes
            if self._is_excluded_path(request.url.path):
                response = await call_next(request)
                return self._add_performance_headers(response, request_id, start_time)
            
            # Optimized rate limiting
            await self._check_rate_limits_optimized(request)
            
            # Process request
            response = await call_next(request)
            
            # Log performance metrics (async in background)
            self._log_performance_async(request, response, start_time, request_id)
            
            return self._add_performance_headers(response, request_id, start_time)
            
        except HTTPException as e:
            # Handle rate limit and other HTTP exceptions efficiently
            return self._create_error_response(e, request_id, start_time)
            
        except asyncio.CancelledError:
            raise
            
        except Exception as e:
            logger.exception(f"Middleware error for request {request_id}: {e}")
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "request_id": request_id
                },
                headers={"X-Request-ID": request_id}
            )
    
    async def _check_rate_limits_optimized(self, request: Request):
        """Optimized rate limiting with caching."""
        # Extract client IP efficiently
        client_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip() or
            request.headers.get("x-real-ip") or
            request.client.host if request.client else "unknown"
        )
        
        # Check cache for recent rate limit results
        cache_key = f"rate_limit:{client_ip}:{request.url.path}"
        cached_result = self._get_from_cache(cache_key)
        
        if cached_result and cached_result.allowed:
            return  # Skip rate limit check if recently allowed
        
        # Perform rate limit check
        from src.utils.rate_limiter import RATE_LIMITS
        
        rate_result = await check_rate_limit(
            f"global:{client_ip}", 
            "global_requests"
        )
        
        if not rate_result.allowed:
            # Get limit from configuration
            config = RATE_LIMITS.get("global_requests")
            limit = config.requests_per_window if config else None
            
            # Cache the denial for a short period to avoid repeated checks
            self._set_cache(cache_key, rate_result)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": rate_result.retry_after,
                    "limit": limit
                }
            )
        
        # Cache successful rate limit for a short period
        self._set_cache(cache_key, rate_result)
    
    def _log_performance_async(self, request: Request, response: Response, start_time: float, request_id: str):
        """Log performance metrics asynchronously."""
        def log_in_background():
            try:
                processing_time = (time.time() - start_time) * 1000
                if processing_time > 1000:  # Only log slow requests
                    logger.warning(
                        f"Slow request {request_id}: {request.method} {request.url.path} "
                        f"took {processing_time:.2f}ms"
                    )
            except Exception as e:
                logger.error(f"Error logging performance for {request_id}: {e}")
        
        # Run in background
        asyncio.create_task(asyncio.to_thread(log_in_background))
    
    def _add_performance_headers(self, response: Response, request_id: str, start_time: float) -> Response:
        """Add performance and debugging headers efficiently."""
        processing_time = (time.time() - start_time) * 1000
        
        response.headers.update({
            "X-Request-ID": request_id,
            "X-Processing-Time": f"{processing_time:.2f}ms",
            "X-Server": "therapy-api",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        })
        
        return response
    
    def _create_error_response(self, error: HTTPException, request_id: str, start_time: float) -> JSONResponse:
        """Create standardized error response."""
        processing_time = (time.time() - start_time) * 1000
        
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": error.detail,
                "request_id": request_id,
                "processing_time_ms": round(processing_time, 2)
            },
            headers={
                "X-Request-ID": request_id,
                "X-Processing-Time": f"{processing_time:.2f}ms"
            }
        )


# Security bearer token handler
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get current authenticated user with optimized performance."""
    token = credentials.credentials
    
    try:
        auth_service = await get_auth_service()
        result = await auth_service.get_current_user(token)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Return minimal user data in the format expected by the application
        return {
            "user": {
                "id": result["user_id"],
                "email": result["email"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error verifying token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication error",
            headers={"WWW-Authenticate": "Bearer"}
        )


# Legacy middleware class alias for backward compatibility
PerformanceMiddleware = PerformanceMiddleware
