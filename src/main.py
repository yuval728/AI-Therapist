"""Main FastAPI application for AI Therapist."""
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import time
from datetime import datetime, timezone

from src.api import (
    auth_router, users_router, sessions_router, health_router, chat_router,
    SecurityMiddleware, CORSMiddleware as CustomCORSMiddleware, ErrorHandlingMiddleware
)
from src.database import get_supabase_client
from src.config import get_settings
from src.utils import log_event, configure_logging

from dotenv import load_dotenv  
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    settings = get_settings()
    configure_logging(structured=False)
    
    log_event(
        event="application_startup",
        environment=settings.environment,
        version=settings.version
    )
    
    # Initialize database connection
    try:
        await get_supabase_client()
        log_event(event="database_connected")
    except Exception as e:
        log_event(
            event="database_connection_failed",
            error=str(e)
        )
    
    yield
    
    # Shutdown
    log_event(event="application_shutdown")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="AI-powered therapy chatbot with advanced safety features",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan
    )
    
    # Add middleware in correct order (last added = first executed)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(SecurityMiddleware, exclude_paths=["/docs", "/redoc", "/openapi.json", "/health"])
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"]
    )
    
    # Include API routers
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(chat_router)  # WebSocket routes
    
    # Root endpoints
    @app.get("/")
    async def root() -> Dict[str, Any]:
        """Root endpoint with API information."""
        return {
            "message": "AI Therapist API",
            "version": settings.version,
            "environment": settings.environment,
            "docs_url": "/docs" if settings.is_development else None,
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @app.get("/info")
    async def api_info() -> Dict[str, Any]:
        """API information and capabilities."""
        return {
            "name": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
            "features": {
                "authentication": True,
                "websocket_chat": True,
                "session_management": True,
                "crisis_detection": settings.security.enable_crisis_detection,
                "pii_detection": settings.security.enable_pii_detection,
                "input_moderation": settings.security.enable_input_moderation,
                "output_moderation": settings.security.enable_output_moderation
            },
            "endpoints": {
                "auth": "/api/auth",
                "users": "/api/users",
                "sessions": "/api/sessions",
                "health": "/api/health",
                "websocket": "/ws/chat"
            }
        }
    
    # Custom exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with structured response."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        log_event(
            event="http_exception",
            request_id=request_id,
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
                "error_code": f"HTTP_{exc.status_code}",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        log_event(
            event="unhandled_exception",
            request_id=request_id,
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    return app


# Create application instance
app = create_app()
