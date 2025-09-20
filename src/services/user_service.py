"""User management service layer."""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from src.database import get_supabase_client
from src.models import User, APIResponse
from src.utils import log_therapy_event, timing_decorator


class UserService:
    """Business logic for user profile management."""
    
    def __init__(self):
        self.supabase_client = None
    
    def _build_user_from_data(self, user_data: Dict[str, Any]) -> User:
        """Build User object from database data."""
        return User(
            id=user_data["id"],
            email=user_data["email"],
            full_name=user_data.get("full_name"),
            preferences=user_data.get("preferences", {}),
            created_at=datetime.fromisoformat(user_data["created_at"].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(user_data["updated_at"].replace('Z', '+00:00'))
        )
    
    def _handle_error(self, event: str, user_id: str, error: Exception, message: str) -> APIResponse:
        """Handle errors consistently with logging."""
        log_therapy_event(
            event=event,
            user_id=user_id,
            error=str(error)
        )
        return APIResponse(
            success=False,
            error=message,
            error_code="INTERNAL_ERROR"
        )
    
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
            
            if not result:
                return APIResponse(
                    success=False,
                    error="User profile not found",
                    error_code="PROFILE_NOT_FOUND"
                )
            
            profile = self._build_user_from_data(result)
            
            return APIResponse(
                success=True,
                data=profile
            )
            
        except Exception as e:
            return self._handle_error("user_profile_retrieval_failed", user_id, e, "Failed to retrieve user profile")
    
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
            result = self.supabase_client.client.table("profiles").update(updates).eq("id", user_id).execute()

            # Handle update error from Supabase
            if getattr(result, "error", None):
                return APIResponse(
                    success=False,
                    error="Failed to update profile",
                    error_code="UPDATE_FAILED"
                )

            # Normalize to User model
            updated = result.data[0] if result and getattr(result, "data", None) else None
            if not updated:
                # Fallback: refetch the profile to return a proper User
                return await self.get_user_profile(user_id)

            profile = self._build_user_from_data(updated)
            return APIResponse(success=True, data=profile)
            
        except Exception as e:
            return self._handle_error("update_profile_error", user_id, e, "Failed to update user profile")
    
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
            return self._handle_error("get_preferences_error", user_id, e, "Failed to retrieve preferences")
    
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
            return self._handle_error("update_preferences_error", user_id, e, "Failed to update preferences")
    
    @timing_decorator("user_get_stats")
    async def get_user_stats(self, user_id: str) -> APIResponse[Dict[str, Any]]:
        """Get comprehensive user statistics and activity summary."""
        await self._ensure_initialized()
        
        try:
            # Calculate date ranges
            now = datetime.now(timezone.utc)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            # Fetch all data in parallel for better performance
            sessions_query = self.supabase_client.client.table("therapy_sessions")\
                .select("id, created_at, emotion, crisis_level, session_summary")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)
            
            memory_query = self.supabase_client.client.table("memory_logs")\
                .select("id, session_id, timestamp, role, message_type")\
                .eq("user_id", user_id)\
                .order("timestamp", desc=True)
            
            crisis_query = self.supabase_client.client.table("crisis_events")\
                .select("id, created_at, crisis_level, resolved")\
                .eq("user_id", user_id)
            
            # Execute queries
            sessions_result = sessions_query.execute()
            memory_result = memory_query.execute()
            crisis_result = crisis_query.execute()
            
            # Extract data with safe defaults
            sessions = sessions_result.data if sessions_result and sessions_result.data else []
            memory_logs = memory_result.data if memory_result and memory_result.data else []
            crisis_events = crisis_result.data if crisis_result and crisis_result.data else []
            
            # Calculate comprehensive stats
            stats = await self._calculate_comprehensive_stats(
                sessions, memory_logs, crisis_events, now, week_ago, month_ago
            )
            
            return APIResponse(success=True, data=stats)
            
        except Exception as e:
            return self._handle_error("get_user_stats_error", user_id, e, "Failed to retrieve user statistics")
    
    async def _calculate_comprehensive_stats(
        self, 
        sessions: List[Dict], 
        memory_logs: List[Dict], 
        crisis_events: List[Dict],
        now: datetime,
        week_ago: datetime, 
        month_ago: datetime
    ) -> Dict[str, Any]:
        """Calculate comprehensive statistics from raw data."""
        # Basic metrics
        total_sessions = len(sessions)
        total_messages = len([log for log in memory_logs if log.get('role') == 'user'])
        crisis_count = len(crisis_events)
        
        # Calculate advanced metrics
        streak_days = self._calculate_streak(sessions, now)
        emotion_distribution = self._calculate_emotion_distribution(sessions, memory_logs)
        weekly_activity = self._calculate_weekly_activity(sessions, memory_logs, week_ago, now)
        improvement_score = self._calculate_improvement_score(sessions, crisis_events, now, month_ago)
        avg_session_duration = self._calculate_avg_session_duration(memory_logs)
        
        # Recent activity
        recent_sessions = sessions[:5] if sessions else []
        week_sessions = [s for s in sessions 
                        if datetime.fromisoformat(s['created_at'].replace('Z', '+00:00')) >= week_ago]
        
        # Weekly summary
        week_messages = [log for log in memory_logs 
                        if datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')) >= week_ago 
                        and log.get('role') == 'user']
        week_crises = [e for e in crisis_events 
                      if datetime.fromisoformat(e['created_at'].replace('Z', '+00:00')) >= week_ago]
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "crisis_events": crisis_count,
            "streak_days": streak_days,
            "improvement_score": improvement_score,
            "emotion_distribution": emotion_distribution,
            "weekly_sessions": [day['sessions'] for day in weekly_activity],  # Frontend compatibility
            "weekly_activity": weekly_activity,   # Detailed activity
            "avg_session_duration": avg_session_duration,
            "recent_sessions": recent_sessions,
            "week_summary": {
                "sessions": len(week_sessions),
                "messages": len(week_messages),
                "crisis_events": len(week_crises)
            },
            "last_session": sessions[0]['created_at'] if sessions else now.isoformat(),
            "last_active": sessions[0]['created_at'] if sessions else now.isoformat()
        }
    
    def _calculate_streak(self, sessions: List[Dict], now: datetime) -> int:
        """Calculate consecutive days with therapy sessions."""
        if not sessions:
            return 0
        
        # Group sessions by date
        session_dates = set()
        for session in sessions:
            session_date = datetime.fromisoformat(session['created_at'].replace('Z', '+00:00')).date()
            session_dates.add(session_date)
        
        # Calculate streak from today backwards
        current_date = now.date()
        streak = 0
        
        while current_date in session_dates:
            streak += 1
            current_date -= timedelta(days=1)
        
        return streak
    
    def _calculate_emotion_distribution(self, sessions: List[Dict], memory_logs: List[Dict]) -> Dict[str, int]:
        """Calculate distribution of emotions from sessions and memory logs."""
        emotion_counts = defaultdict(int)
        
        # Collect emotions from all sources
        for session in sessions:
            emotion = session.get('emotion')
            if emotion and emotion.strip():
                emotion_counts[emotion.lower()] += 1
        
        for log in memory_logs:
            emotion = log.get('emotion')
            if emotion and emotion.strip():
                emotion_counts[emotion.lower()] += 1
        
        # Ensure common emotions are present with defaults
        common_emotions = ['happy', 'sad', 'anxious', 'angry', 'calm', 'stressed', 'neutral']
        distribution = {emotion: emotion_counts.get(emotion, 0) for emotion in common_emotions}
        
        # Add any additional emotions found
        for emotion, count in emotion_counts.items():
            if emotion not in distribution:
                distribution[emotion] = count
        
        return distribution
    
    def _calculate_weekly_activity(self, sessions: List[Dict], memory_logs: List[Dict], 
                                 week_ago: datetime, now: datetime) -> List[Dict[str, Any]]:
        """Calculate daily activity for the past week."""
        daily_activity = []
        
        for i in range(7):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            # Filter sessions and messages for this day
            day_sessions = [
                s for s in sessions 
                if day_start <= datetime.fromisoformat(s['created_at'].replace('Z', '+00:00')) < day_end
            ]
            
            day_messages = [
                log for log in memory_logs 
                if (day_start <= datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')) < day_end 
                    and log.get('role') == 'user')
            ]
            
            daily_activity.append({
                "date": day.strftime("%Y-%m-%d"),
                "day": day.strftime("%a"),
                "sessions": len(day_sessions),
                "messages": len(day_messages)
            })
        
        return list(reversed(daily_activity))  # Chronological order
    
    def _calculate_improvement_score(self, sessions: List[Dict], crisis_events: List[Dict], 
                                   now: datetime, month_ago: datetime) -> float:
        """Calculate improvement score based on various factors (0-10 scale)."""
        if not sessions:
            return 5.0  # Neutral score for new users
        
        score = 5.0  # Start with neutral
        
        # Recent activity (0-2 points)
        recent_sessions = [
            s for s in sessions 
            if datetime.fromisoformat(s['created_at'].replace('Z', '+00:00')) >= month_ago
        ]
        
        session_count = len(recent_sessions)
        if session_count >= 20:
            score += 2.0
        elif session_count >= 10:
            score += 1.5
        elif session_count >= 5:
            score += 1.0
        elif session_count >= 1:
            score += 0.5
        
        # Crisis management (0-3 points)
        recent_crises = [
            e for e in crisis_events 
            if datetime.fromisoformat(e['created_at'].replace('Z', '+00:00')) >= month_ago
        ]
        
        crisis_count = len(recent_crises)
        if crisis_count == 0:
            score += 2.0  # No recent crises
        elif crisis_count <= 2:
            score += 1.0  # Few crises
        elif crisis_count <= 5:
            score += 0.5  # Moderate crises
        
        # Crisis resolution rate (0-1 point)
        if recent_crises:
            resolved_count = len([e for e in recent_crises if e.get('resolved', False)])
            resolution_rate = resolved_count / len(recent_crises)
            score += resolution_rate
        
        # Engagement trend (0-1 point)
        if len(sessions) >= 2:
            mid_point = len(sessions) // 2
            early_sessions = sessions[mid_point:]  # Older sessions
            late_sessions = sessions[:mid_point]   # Recent sessions
            
            if len(late_sessions) > len(early_sessions):
                score += 1.0  # Increasing engagement
            elif len(late_sessions) == len(early_sessions):
                score += 0.5  # Stable engagement
        
        return max(0.0, min(10.0, round(score, 1)))
    
    def _calculate_avg_session_duration(self, memory_logs: List[Dict]) -> float:
        """Calculate average session duration in minutes from memory logs."""
        if not memory_logs:
            return 0.0
        
        # Group logs by session_id and find start/end times
        sessions_data = {}
        for log in memory_logs:
            session_id = log.get('session_id')
            if not session_id:
                continue
            
            timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
            
            if session_id not in sessions_data:
                sessions_data[session_id] = {'start': timestamp, 'end': timestamp}
            else:
                sessions_data[session_id]['start'] = min(sessions_data[session_id]['start'], timestamp)
                sessions_data[session_id]['end'] = max(sessions_data[session_id]['end'], timestamp)
        
        # Calculate durations for sessions with actual activity
        durations = []
        for session_data in sessions_data.values():
            duration_minutes = (session_data['end'] - session_data['start']).total_seconds() / 60
            if duration_minutes > 0:  # Only count sessions with actual duration
                durations.append(duration_minutes)
        
        return round(sum(durations) / len(durations), 1) if durations else 0.0
    
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
            
            # Execute deletions efficiently
            for table in tables_to_clean:
                delete_query = self.supabase_client.client.table(table).delete()
                if table == "profiles":
                    delete_query.eq("id", user_id).execute()
                else:
                    delete_query.eq("user_id", user_id).execute()

            # Delete from auth if service role key is available
            if self.supabase_client.service_role_key:
                try:
                    self.supabase_client.client.auth.admin.delete_user(user_id)
                except Exception as auth_error:
                    log_therapy_event(
                        event="user_auth_delete_failed",
                        user_id=user_id,
                        error=str(auth_error)
                    )
            
            log_therapy_event(event="user_account_deleted", user_id=user_id)
            return APIResponse(success=True, message="Account deleted successfully")
            
        except Exception as e:
            return self._handle_error("delete_account_error", user_id, e, "Failed to delete account")


# Global service instance
_user_service: Optional[UserService] = None


async def get_user_service() -> UserService:
    """Get initialized user service."""
    global _user_service
    
    if _user_service is None:
        _user_service = UserService()
        await _user_service._ensure_initialized()
    
    return _user_service
