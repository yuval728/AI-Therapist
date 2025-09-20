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
async def health_check() -> APIResponse[Dict[str, Any]]:
    """Basic health check - is the service alive and database connected?"""
    try:
        # Quick database connectivity test
        supabase_client = await get_supabase_client()
        if not supabase_client._initialized:
            health_data = {
                "status": "unhealthy",
                "reason": "database_disconnected",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            return APIResponse(
                success=True,
                data=health_data
            )
        
        health_data = {
            "status": "healthy",
            "service": "AI Therapist API",
            "version": get_settings().version,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return APIResponse(
            success=True,
            data=health_data
        )
        
    except Exception as e:
        log_event(event="health_check_failed", error=str(e))
        health_data = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return APIResponse(
            success=True,
            data=health_data
        )


@router.get("/ready")
async def readiness_check() -> APIResponse[Dict[str, Any]]:
    """Kubernetes-style readiness probe."""
    health_result = await health_check()
    
    # Ready if healthy
    is_ready = health_result.data.get("status") == "healthy" if health_result.data else False
    
    return APIResponse(
        success=True,
        data={
            "ready": is_ready,
            "status": health_result.data.get("status", "unknown") if health_result.data else "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@router.get("/live")
async def liveness_check() -> APIResponse[Dict[str, Any]]:
    """Kubernetes-style liveness probe - just verify service is responding."""
    return APIResponse(
        success=True,
        data={
            "alive": True,
            "service": "AI Therapist API",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@router.get("/detailed")
async def detailed_health_check() -> APIResponse[Dict[str, Any]]:
    """Detailed health check with component status."""
    try:
        supabase_client = await get_supabase_client()
        
        # Basic health data
        health_data = {
            "status": "healthy",
            "service": "AI Therapist API",
            "version": get_settings().version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": []
        }
        
        # Check database connection
        db_status = "healthy"
        db_error = None
        try:
            if not supabase_client._initialized:
                db_status = "unhealthy"
                db_error = "Database not initialized"
            else:
                # Quick test query
                test_result = supabase_client.client.table("profiles").select("count", count="exact").limit(1).execute()
                if hasattr(test_result, 'error') and test_result.error:
                    db_status = "unhealthy"
                    db_error = str(test_result.error)
        except Exception as e:
            db_status = "unhealthy"
            db_error = str(e)
        
        health_data["components"].append({
            "name": "database",
            "status": db_status,
            "error": db_error
        })
        
        # Overall status based on components
        if any(comp["status"] != "healthy" for comp in health_data["components"]):
            health_data["status"] = "unhealthy"
        
        return APIResponse(
            success=True,
            data=health_data
        )
        
    except Exception as e:
        log_event(event="detailed_health_check_failed", error=str(e))
        health_data = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": []
        }
        return APIResponse(
            success=True,
            data=health_data
        )


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
