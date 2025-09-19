"""Simple and efficient health check API routes."""
from fastapi import APIRouter
from datetime import datetime, timezone
from typing import Dict, Any

from src.database.supabase_client import get_supabase_client
from src.models import APIResponse
from src.config import get_settings
from src.utils import log_event

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check - is the service alive and database connected?"""
    try:
        # Quick database connectivity test
        supabase_client = await get_supabase_client()
        if not supabase_client._initialized:
            return {
                "status": "unhealthy",
                "reason": "database_disconnected",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        return {
            "status": "healthy",
            "service": "AI Therapist API",
            "version": get_settings().version,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        log_event(event="health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Kubernetes-style readiness probe."""
    health_result = await health_check()
    
    # Ready if healthy
    is_ready = health_result.get("status") == "healthy"
    
    return {
        "ready": is_ready,
        "status": health_result.get("status", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """Kubernetes-style liveness probe - just verify service is responding."""
    return {
        "alive": True,
        "service": "AI Therapist API",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/metrics")
async def get_basic_metrics() -> APIResponse[Dict[str, Any]]:
    """Get basic application metrics."""
    try:
        supabase_client = await get_supabase_client()
        
        # Get basic counts if database is available
        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": get_settings().environment,
            "version": get_settings().version
        }
        
        if supabase_client._initialized:
            try:
                # Get basic counts
                users_result = supabase_client.client.table("profiles").select("count", count="exact").execute()
                sessions_result = supabase_client.client.table("therapy_sessions").select("count", count="exact").execute()
                
                metrics.update({
                    "users_count": users_result.count if users_result and hasattr(users_result, 'count') else 0,
                    "sessions_count": sessions_result.count if sessions_result and hasattr(sessions_result, 'count') else 0,
                    "database_status": "connected"
                })
            except Exception:
                metrics["database_status"] = "error"
        else:
            metrics["database_status"] = "disconnected"
        
        return APIResponse(
            success=True,
            data=metrics,
            message="Basic metrics retrieved successfully"
        )
        
    except Exception as e:
        log_event(event="metrics_failed", error=str(e))
        return APIResponse(
            success=False,
            error="Failed to retrieve metrics",
            error_code="METRICS_ERROR"
        )
