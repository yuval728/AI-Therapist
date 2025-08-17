"""Health check and system status API routes."""
from typing import Dict, Any
from fastapi import APIRouter, status
from datetime import datetime, timezone
import asyncio

from src.database import get_supabase_client
from src.models import APIResponse
from src.config import get_settings
from src.utils import log_therapy_event

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check() -> APIResponse[Dict[str, Any]]:
    """Basic health check endpoint."""
    return APIResponse(
        success=True,
        data={
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "AI Therapist API"
        },
        message="Service is running"
    )


@router.get("/detailed")
async def detailed_health_check() -> APIResponse[Dict[str, Any]]:
    """Detailed health check with dependency status."""
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "AI Therapist API",
        "version": get_settings().version,
        "environment": get_settings().environment,
        "dependencies": {}
    }
    
    # Check database connection
    try:
        supabase_client = await get_supabase_client()
        # Simple query to test connection
        result = supabase_client.client.table("profiles").select("count", count="exact").limit(1).execute()
        health_data["dependencies"]["database"] = {
            "status": "healthy",
            "response_time_ms": 0  # Could add timing here
        }
    except Exception as e:
        health_data["dependencies"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_data["status"] = "degraded"
    
    # Check configuration
    settings = get_settings()
    config_issues = []
    
    if not settings.models.google_api_key:
        config_issues.append("Missing Google API key")
    if not settings.database.supabase_url:
        config_issues.append("Missing Supabase URL")
    if not settings.database.supabase_key:
        config_issues.append("Missing Supabase key")
    
    health_data["dependencies"]["configuration"] = {
        "status": "healthy" if not config_issues else "unhealthy",
        "issues": config_issues
    }
    
    if config_issues:
        health_data["status"] = "degraded"
    
    return APIResponse(
        success=True,
        data=health_data
    )


@router.get("/metrics")
async def get_metrics() -> APIResponse[Dict[str, Any]]:
    """Get basic system metrics."""
    try:
        supabase_client = await get_supabase_client()
        
        # Get basic counts
        users_result = supabase_client.client.table("profiles").select("count", count="exact").execute()
        sessions_result = supabase_client.client.table("therapy_sessions").select("count", count="exact").execute()
        messages_result = supabase_client.client.table("memory_logs").select("count", count="exact").execute()
        
        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "users": {
                "total": users_result.count if users_result else 0
            },
            "sessions": {
                "total": sessions_result.count if sessions_result else 0
            },
            "messages": {
                "total": messages_result.count if messages_result else 0
            },
            "system": {
                "uptime_seconds": 0,  # Could track actual uptime
                "environment": get_settings().environment
            }
        }
        
        return APIResponse(
            success=True,
            data=metrics
        )
        
    except Exception as e:
        log_therapy_event(
            event="metrics_error",
            error=str(e)
        )
        return APIResponse(
            success=False,
            error="Failed to retrieve metrics",
            error_code="METRICS_ERROR"
        )


@router.get("/readiness")
async def readiness_check() -> APIResponse[Dict[str, Any]]:
    """Readiness check for container orchestration."""
    try:
        # Check if all critical services are ready
        supabase_client = await get_supabase_client()
        
        # Test database connectivity
        result = supabase_client.client.table("profiles").select("count", count="exact").limit(1).execute()
        
        return APIResponse(
            success=True,
            data={
                "status": "ready",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            data={
                "status": "not_ready",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            },
            error="Service not ready"
        )


@router.get("/liveness")
async def liveness_check() -> APIResponse[Dict[str, Any]]:
    """Liveness check for container orchestration."""
    return APIResponse(
        success=True,
        data={
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
