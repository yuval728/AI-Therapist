"""High-Performance FastAPI application for AI Therapist with optimizations."""
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime, timezone

from src.api import (
    auth_router, users_router, sessions_router, health_router, chat_router
)
from src.api.middleware import PerformanceMiddleware
from src.utils.cache_manager import get_cache_manager
from src.database.supabase_client import get_supabase_client
from src.services import get_auth_service, get_user_service, get_session_service, get_chat_service
from src.config import get_settings
from src.utils import log_event, configure_logging

from dotenv import load_dotenv  
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Optimized application lifespan management with proper resource initialization."""
    # Startup
    settings = get_settings()
    configure_logging()
    
    log_event(
        event="application_startup",
        environment=settings.environment,
        version=settings.version
    )
    
    try:
        # Initialize core components
        await initialize_core_components()
        
        # Initialize services (they'll be lazy-loaded when first used)
        log_event(event="services_ready", message="Services will be initialized on first use")
        
        log_event(event="application_ready")
        
    except Exception as e:
        log_event(
            event="application_startup_failed",
            error=str(e)
        )
        raise
    
    yield
    
    # Shutdown
    await shutdown_components()
    log_event(event="application_shutdown")


async def initialize_core_components():
    """Initialize core performance components."""
    # Initialize Supabase client
    supabase_client = await get_supabase_client()
    if not supabase_client._initialized:
        raise RuntimeError("Failed to initialize Supabase client")
    
    # Initialize cache manager
    cache_manager = await get_cache_manager()
    cache_init_success = cache_manager._initialized
    if not cache_init_success:
        log_event(event="cache_initialization_failed", level="warning")
    
    log_event(
        event="core_components_initialized",
        supabase_client=supabase_client._initialized,
        cache_manager=cache_init_success
    )


async def check_services_health():
    """Check health of all services."""
    services_health = {}
    
    try:
        auth_service = await get_auth_service()
        services_health["auth"] = {"status": "healthy"}
    except Exception as e:
        services_health["auth"] = {"status": "unhealthy", "error": str(e)}
    
    try:
        user_service = await get_user_service()
        services_health["user"] = {"status": "healthy"}
    except Exception as e:
        services_health["user"] = {"status": "unhealthy", "error": str(e)}
    
    try:
        session_service = await get_session_service()
        services_health["session"] = {"status": "healthy"}
    except Exception as e:
        services_health["session"] = {"status": "unhealthy", "error": str(e)}
    
    try:
        chat_service = await get_chat_service()
        services_health["chat"] = {"status": "healthy"}
    except Exception as e:
        services_health["chat"] = {"status": "unhealthy", "error": str(e)}
    
    return services_health


async def shutdown_components():
    """Gracefully shutdown all components."""
    try:
        # Services will be garbage collected automatically
        # No explicit shutdown needed for services
        
        # Close Supabase client
        supabase_client = await get_supabase_client()
        await supabase_client.close()
        
        # Close cache connections
        cache_manager = await get_cache_manager()
        if cache_manager.redis_client:
            await cache_manager.redis_client.aclose()
        
        log_event(event="components_shutdown_complete")
        
    except Exception as e:
        log_event(
            event="shutdown_error",
            error=str(e)
        )


def create_app() -> FastAPI:
    """Create and configure high-performance FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="High-performance AI-powered therapy chatbot with advanced safety features and API-based chat",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan
    )
    
    # Add optimized middleware in correct order (last added = first executed)
    app.add_middleware(
        PerformanceMiddleware, 
        exclude_paths=["/docs", "/redoc", "/openapi.json", "/health", "/api/health"]
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
    )
    
    # Include API routers
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")  # Chat API routes
    
    # Enhanced root endpoints
    @app.get("/")
    async def root() -> Dict[str, Any]:
        """Root endpoint with comprehensive API information."""
        cache_manager = await get_cache_manager()
        return {
            "message": "High-Performance AI Therapist API",
            "version": settings.version,
            "environment": settings.environment,
            "docs_url": "/docs" if settings.is_development else None,
            "status": "healthy",
            "performance_features": {
                "supabase_pooling": True,
                "redis_caching": cache_manager._initialized,
                "rate_limiting": True,
                "async_processing": True,
                "api_chat": True
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @app.get("/info")
    async def api_info() -> Dict[str, Any]:
        """Enhanced API information with performance metrics."""
        services_health = await check_services_health()
        supabase_client = await get_supabase_client()
        cache_manager = await get_cache_manager()
        
        return {
            "name": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
            "features": {
                "authentication": True,
                "api_chat": True,
                "session_management": True,
                "crisis_detection": settings.security.enable_crisis_detection,
                "pii_detection": settings.security.enable_pii_detection,
                "input_moderation": settings.security.enable_input_moderation,
                "output_moderation": settings.security.enable_output_moderation,
                "supabase_pooling": supabase_client._initialized,
                "caching": cache_manager._initialized,
                "rate_limiting": True
            },
            "endpoints": {
                "auth": "/api/auth",
                "users": "/api/users",
                "sessions": "/api/sessions",
                "health": "/api/health",
                "chat": "/api/chat"
            },
            "services_health": services_health,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @app.get("/metrics")
    async def metrics() -> Dict[str, Any]:
        """Performance metrics endpoint."""
        services_health = await check_services_health()
        supabase_client = await get_supabase_client()
        cache_manager = await get_cache_manager()
        
        return {
            "supabase": {
                "initialized": supabase_client._initialized,
                "connection_pooling": "managed_by_supabase"
            },
            "cache": {
                "initialized": cache_manager._initialized,
                "type": "redis" if cache_manager.redis_client else "memory"
            },
            "services": services_health,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # Enhanced exception handlers with performance logging
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with performance context."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        log_event(
            event="http_exception",
            request_id=request_id,
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
                "error_code": f"HTTP_{exc.status_code}",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            headers=getattr(exc, "headers", {})
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions with enhanced logging."""
        # Let CancelledError propagate
        if isinstance(exc, asyncio.CancelledError):
            raise exc
            
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        log_event(
            event="unhandled_exception",
            request_id=request_id,
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method
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


# Create optimized application instance
app = create_app()
