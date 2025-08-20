"""User management service layer."""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from src.database import get_supabase_client
from src.models import User, APIResponse
from src.utils import log_therapy_event, timing_decorator, ValidationError


class UserService:
    """Business logic for user profile management."""
    
    def __init__(self):
        self.supabase_client = None
    
    async def _ensure_initialized(self):
        """Ensure database client is initialized."""
        if self.supabase_client is None:
            self.supabase_client = await get_supabase_client()
    
    @timing_decorator("user_get_profile")
    async def get_user_profile(self, user_id: str) -> APIResponse[User]:
        """Get user profile by ID."""
        await self._ensure_initialized()
        
        try:
            result = await self.supabase_client.get_user_profile(user_id)
            
            if not result.success or not result.data:
                return APIResponse(
                    success=False,
                    error="User profile not found",
                    error_code="PROFILE_NOT_FOUND"
                )
            
            profile_data = result.data[0]
            profile = User(
                id=profile_data["id"],
                email=profile_data["email"],
                full_name=profile_data.get("full_name"),
                preferences=profile_data.get("preferences", {}),
                created_at=datetime.fromisoformat(profile_data["created_at"].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(profile_data["updated_at"].replace('Z', '+00:00'))
            )
            
            return APIResponse(
                success=True,
                data=profile
            )
            
        except Exception as e:
            log_therapy_event(
                event="get_profile_error",
                user_id=user_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to retrieve user profile",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("user_update_profile")
    async def update_user_profile(
        self, 
        user_id: str, 
        updates: Dict[str, Any]
    ) -> APIResponse[User]:
        """Update user profile."""
        await self._ensure_initialized()
        
        try:
            # Validate updates
            allowed_fields = {"full_name", "preferences"}
            invalid_fields = set(updates.keys()) - allowed_fields
            
            if invalid_fields:
                return APIResponse(
                    success=False,
                    error=f"Invalid fields: {', '.join(invalid_fields)}",
                    error_code="VALIDATION_ERROR"
                )
            
            # Add timestamp
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Update in database
            result = await self.supabase_client.client.table("profiles").update(updates).eq("id", user_id).execute()
            
            if result.error:
                return APIResponse(
                    success=False,
                    error="Failed to update profile",
                    error_code="UPDATE_FAILED"
                )
            
            # Get updated profile
            return await self.get_user_profile(user_id)
            
        except Exception as e:
            log_therapy_event(
                event="update_profile_error",
                user_id=user_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to update user profile",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("user_get_preferences")
    async def get_user_preferences(self, user_id: str) -> APIResponse[Dict[str, Any]]:
        """Get user preferences."""
        await self._ensure_initialized()
        
        try:
            profile_result = await self.get_user_profile(user_id)
            
            if not profile_result.success:
                return APIResponse(
                    success=False,
                    error=profile_result.error,
                    error_code=profile_result.error_code
                )
            
            return APIResponse(
                success=True,
                data=profile_result.data.preferences
            )
            
        except Exception as e:
            log_therapy_event(
                event="get_preferences_error",
                user_id=user_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to retrieve preferences",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("user_update_preferences")
    async def update_user_preferences(
        self, 
        user_id: str, 
        preferences: Dict[str, Any]
    ) -> APIResponse[Dict[str, Any]]:
        """Update user preferences."""
        await self._ensure_initialized()
        
        try:
            # Get current profile
            current_profile = await self.get_user_profile(user_id)
            if not current_profile.success:
                return APIResponse(
                    success=False,
                    error=current_profile.error,
                    error_code=current_profile.error_code
                )
            
            # Merge preferences
            current_preferences = current_profile.data.preferences or {}
            updated_preferences = {**current_preferences, **preferences}
            
            # Update profile
            update_result = await self.update_user_profile(
                user_id, 
                {"preferences": updated_preferences}
            )
            
            if not update_result.success:
                return APIResponse(
                    success=False,
                    error=update_result.error,
                    error_code=update_result.error_code
                )
            
            return APIResponse(
                success=True,
                data=updated_preferences,
                message="Preferences updated successfully"
            )
            
        except Exception as e:
            log_therapy_event(
                event="update_preferences_error",
                user_id=user_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to update preferences",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("user_get_stats")
    async def get_user_stats(self, user_id: str) -> APIResponse[Dict[str, Any]]:
        """Get user statistics and activity summary."""
        await self._ensure_initialized()
        
        try:
            # Get therapy sessions count
            sessions_result = await self.supabase_client.client.table("therapy_sessions")\
                .select("count", count="exact")\
                .eq("user_id", user_id)\
                .execute()
            
            # Get memory logs count
            memory_result = await self.supabase_client.client.table("memory_logs")\
                .select("count", count="exact")\
                .eq("user_id", user_id)\
                .execute()
            
            # Get crisis events count
            crisis_result = await self.supabase_client.client.table("crisis_events")\
                .select("count", count="exact")\
                .eq("user_id", user_id)\
                .execute()
            
            # Get recent activity
            recent_sessions = await self.supabase_client.client.table("therapy_sessions")\
                .select("created_at, emotion, crisis_level")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(5)\
                .execute()
            
            stats = {
                "total_sessions": sessions_result.count if sessions_result else 0,
                "total_messages": memory_result.count if memory_result else 0,
                "crisis_events": crisis_result.count if crisis_result else 0,
                "recent_sessions": recent_sessions.data if recent_sessions else [],
                "last_active": datetime.now(timezone.utc).isoformat()
            }
            
            return APIResponse(
                success=True,
                data=stats
            )
            
        except Exception as e:
            log_therapy_event(
                event="get_user_stats_error",
                user_id=user_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to retrieve user statistics",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("user_delete_account")
    async def delete_user_account(self, user_id: str) -> APIResponse[None]:
        """Delete user account and all associated data."""
        await self._ensure_initialized()
        
        try:
            # Delete in order due to foreign key constraints
            tables_to_clean = [
                "performance_metrics",
                "security_events", 
                "crisis_events",
                "documents",
                "memory_logs",
                "therapy_sessions",
                "profiles"
            ]
            
            for table in tables_to_clean:
                await self.supabase_client.client.table(table)\
                    .delete()\
                    .eq("user_id", user_id)\
                    .execute()
            
            log_therapy_event(
                event="user_account_deleted",
                user_id=user_id
            )
            
            return APIResponse(
                success=True,
                message="Account deleted successfully"
            )
            
        except Exception as e:
            log_therapy_event(
                event="delete_account_error",
                user_id=user_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to delete account",
                error_code="INTERNAL_ERROR"
            )


# Global service instance
_user_service: Optional[UserService] = None


async def get_user_service() -> UserService:
    """Get initialized user service."""
    global _user_service
    
    if _user_service is None:
        _user_service = UserService()
        await _user_service._ensure_initialized()
    
    return _user_service
