"""API middleware for security, logging, and request handling."""
from typing import Callable, Optional
import time
import uuid
from fastapi import Request, Response, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import asyncio

from src.services import get_auth_service
from src.utils import log_therapy_event
from src.config import get_settings


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for authentication and rate limiting."""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            # Health (both root and API-prefixed)
            "/health",
            "/api/health",
            "/api/health/detailed",
            "/api/health/metrics",
            "/api/health/readiness",
            "/api/health/liveness",
            # WebSocket base (handshake typically bypasses HTTP middleware, but safe to exclude)
            "/ws"
        ]
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security middleware."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        try:
            # Skip security for excluded paths
            if any(request.url.path.startswith(path) for path in self.exclude_paths):
                response = await call_next(request)
                return self._add_response_headers(response, request_id, start_time)
            
            
            # Process request
            response = await call_next(request)
            
            # Log request
            await self._log_request(request, response, start_time, request_id)
            
            return self._add_response_headers(response, request_id, start_time)
            
        except asyncio.CancelledError:
            # Let cancellation errors propagate
            raise
        except Exception as e:
            # Log error
            log_therapy_event(
                event="middleware_error",
                request_id=request_id,
                path=request.url.path,
                error=str(e)
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error", "request_id": request_id}
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check common proxy headers in order of preference
        for header in ["X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP"]:
            value = request.headers.get(header)
            if value:
                return value.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    
    async def _log_request(
        self, 
        request: Request, 
        response: Response, 
        start_time: float,
        request_id: str
    ):
        """Log request details."""
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        log_therapy_event(
            event="api_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("User-Agent", "unknown")
        )
    
    def _add_response_headers(
        self, 
        response: Response, 
        request_id: str, 
        start_time: float
    ) -> Response:
        """Add security and tracking headers to response."""
        headers = {
            "X-Request-ID": request_id,
            "X-Response-Time": str(round((time.time() - start_time) * 1000, 2)),
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block"
        }
        
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


class AuthenticationMiddleware:
    """Authentication middleware for protected routes."""
    
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
        self.auth_service = None
    
    async def _ensure_initialized(self):
        """Ensure auth service is initialized."""
        if self.auth_service is None:
            self.auth_service = await get_auth_service()
    
    async def __call__(self, request: Request) -> Optional[dict]:
        """Authenticate request and return user info."""
        await self._ensure_initialized()
        
        try:
            # Get authorization header
            credentials: HTTPAuthorizationCredentials = await self.security(request)
            
            if not credentials:
                return None
            
            # Validate token
            auth_result = await self.auth_service.get_current_user(credentials.credentials)
            
            if not auth_result.success:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            
            return auth_result.data
            
        except HTTPException:
            raise
        except Exception as e:
            log_therapy_event(
                event="auth_middleware_error",
                error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication error"
            )


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS middleware for cross-origin requests."""
    
    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle CORS for requests."""
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response)
            return response
        
        # Process request
        response = await call_next(request)
        self._add_cors_headers(response)
        
        return response
    
    def _add_cors_headers(self, response: Response):
        """Add CORS headers to response."""
        cors_headers = {
            "Access-Control-Allow-Origin": ", ".join(self.settings.cors_origins),
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Allow-Credentials": str(self.settings.cors_allow_credentials).lower(),
            "Access-Control-Max-Age": "86400"  # 24 hours
        }
        
        for key, value in cors_headers.items():
            response.headers[key] = value


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle errors globally."""
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as e:
            # Let FastAPI handle HTTP exceptions
            raise e
            
        except asyncio.CancelledError:
            # Let cancellation errors propagate
            raise
            
        except Exception as e:
            # Log unexpected errors
            request_id = getattr(request.state, 'request_id', 'unknown')
            
            log_therapy_event(
                event="unhandled_error",
                request_id=request_id,
                path=request.url.path,
                method=request.method,
                error=str(e),
                error_type=type(e).__name__
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "message": "An unexpected error occurred"
                }
            )


# Authentication dependency
auth_middleware = AuthenticationMiddleware()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())
) -> dict:
    """Dependency to get current authenticated user using Bearer token.
    This also registers the HTTP Bearer security scheme in OpenAPI, enabling the
    "Authorize" button in Swagger UI.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    auth_service = await get_auth_service()
    auth_result = await auth_service.get_current_user(credentials.credentials)

    if not auth_result.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return auth_result.data


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """Dependency to get current user if authenticated, None otherwise.
    Uses Bearer token when provided so it appears in OpenAPI but does not error if missing.
    """
    if not credentials or not credentials.credentials:
        return None

    try:
        auth_service = await get_auth_service()
        auth_result = await auth_service.get_current_user(credentials.credentials)
        return auth_result.data if auth_result.success else None
    except Exception:
        return None
