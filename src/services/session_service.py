"""Session management service layer."""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid

from src.database import get_supabase_client
from src.models import (
    TherapySession, SessionMessage, EmotionType, CrisisLevel, 
    MessageType, APIResponse, PaginationParams
)
from src.utils import log_therapy_event, timing_decorator


class SessionService:
    """Business logic for therapy session management."""
    
    def __init__(self):
        self.supabase_client = None
    
    async def _ensure_initialized(self):
        """Ensure database client is initialized."""
        if self.supabase_client is None:
            self.supabase_client = await get_supabase_client()
    
    @timing_decorator("session_create")
    async def create_session(
        self, 
        user_id: str, 
        emotion: Optional[EmotionType] = None,
        crisis_level: Optional[CrisisLevel] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> APIResponse[TherapySession]:
        """Create a new therapy session."""
        await self._ensure_initialized()
        
        try:
            session = TherapySession(
                user_id=user_id,
                emotion_detected=emotion or EmotionType.NEUTRAL,
                crisis_level=crisis_level or CrisisLevel.NONE,
            )
            
            result = await self.supabase_client.create_therapy_session(session)
            
            if not result.success:
                # Log reason from DB for easier debugging
                log_therapy_event(
                    event="session_creation_failed",
                    user_id=user_id,
                    error=result.error or "unknown_error"
                )
                return APIResponse(
                    success=False,
                    error="Failed to create therapy session",
                    error_code="SESSION_CREATE_FAILED"
                )
            
            log_therapy_event(
                event="session_created",
                user_id=user_id,
                session_id=session.id
            )
            
            return APIResponse(
                success=True,
                data=session,
                message="Therapy session created successfully"
            )
            
        except Exception as e:
            log_therapy_event(
                event="session_create_error",
                user_id=user_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to create therapy session",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("session_get")
    async def get_session(self, user_id: str, session_id: str) -> APIResponse[TherapySession]:
        """Get therapy session by ID."""
        await self._ensure_initialized()
        
        try:
            result = await self.supabase_client.client.table("therapy_sessions")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("session_id", session_id)\
                .execute()
            
            if not result.data:
                return APIResponse(
                    success=False,
                    error="Session not found",
                    error_code="SESSION_NOT_FOUND"
                )
            
            session_data = result.data[0]
            session = TherapySession(
                id=session_data["session_id"],
                user_id=session_data["user_id"],
                emotion_detected=EmotionType(session_data.get("emotion", "neutral")) if session_data.get("emotion") else EmotionType.NEUTRAL,
                crisis_level=CrisisLevel(session_data.get("crisis_level", "none")) if session_data.get("crisis_level") else CrisisLevel.NONE,
                created_at=datetime.fromisoformat(session_data["created_at"].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(session_data["updated_at"].replace('Z', '+00:00'))
            )
            
            return APIResponse(
                success=True,
                data=session
            )
            
        except Exception as e:
            log_therapy_event(
                event="session_get_error",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to retrieve session",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("session_list")
    async def list_user_sessions(
        self, 
        user_id: str, 
        pagination: Optional[PaginationParams] = None
    ) -> APIResponse[List[TherapySession]]:
        """List user's therapy sessions with pagination."""
        await self._ensure_initialized()
        
        try:
            pagination = pagination or PaginationParams()
            
            query = self.supabase_client.client.table("therapy_sessions")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .range(pagination.offset, pagination.offset + pagination.limit - 1)
            
            result = await query.execute()
            
            sessions = []
            for session_data in result.data:
                session = TherapySession(
                    id=session_data["session_id"],
                    user_id=session_data["user_id"],
                    emotion_detected=EmotionType(session_data.get("emotion", "neutral")) if session_data.get("emotion") else EmotionType.NEUTRAL,
                    crisis_level=CrisisLevel(session_data.get("crisis_level", "none")) if session_data.get("crisis_level") else CrisisLevel.NONE,
                    created_at=datetime.fromisoformat(session_data["created_at"].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(session_data["updated_at"].replace('Z', '+00:00'))
                )
                sessions.append(session)
            
            return APIResponse(
                success=True,
                data=sessions,
                metadata={
                    "total": len(sessions),
                    "offset": pagination.offset,
                    "limit": pagination.limit
                }
            )
            
        except Exception as e:
            log_therapy_event(
                event="session_list_error",
                user_id=user_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to retrieve sessions",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("session_update")
    async def update_session(
        self, 
        user_id: str, 
        session_id: str, 
        updates: Dict[str, Any]
    ) -> APIResponse[TherapySession]:
        """Update therapy session."""
        await self._ensure_initialized()
        
        try:
            # Validate updates
            allowed_fields = {"emotion", "crisis_level", "metadata", "ended_at"}
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
            result = await self.supabase_client.client.table("therapy_sessions")\
                .update(updates)\
                .eq("user_id", user_id)\
                .eq("session_id", session_id)\
                .execute()
            
            if result.error:
                return APIResponse(
                    success=False,
                    error="Failed to update session",
                    error_code="UPDATE_FAILED"
                )
            
            # Get updated session
            return await self.get_session(user_id, session_id)
            
        except Exception as e:
            log_therapy_event(
                event="session_update_error",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to update session",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("session_end")
    async def end_session(self, user_id: str, session_id: str) -> APIResponse[TherapySession]:
        """End a therapy session."""
        await self._ensure_initialized()
        
        try:
            updates = {
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = await self.update_session(user_id, session_id, updates)
            
            if result.success:
                log_therapy_event(
                    event="session_ended",
                    user_id=user_id,
                    session_id=session_id
                )
            
            return result
            
        except Exception as e:
            log_therapy_event(
                event="session_end_error",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to end session",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("session_get_messages")
    async def get_session_messages(
        self, 
        user_id: str, 
        session_id: str,
        pagination: Optional[PaginationParams] = None
    ) -> APIResponse[List[SessionMessage]]:
        """Get messages for a therapy session."""
        await self._ensure_initialized()
        
        try:
            pagination = pagination or PaginationParams()
            
            result = await self.supabase_client.get_memory_logs(
                user_id=user_id,
                session_id=session_id,
                limit=pagination.limit,
                offset=pagination.offset
            )
            
            if not result.success:
                return APIResponse(
                    success=False,
                    error="Failed to retrieve session messages",
                    error_code="MESSAGES_FETCH_FAILED"
                )
            
            messages = []
            for msg_data in result.data:
                # Prefer 'timestamp' column from memory_logs, fallback to 'created_at'
                ts_raw = msg_data.get("timestamp") or msg_data.get("created_at")
                ts = datetime.fromisoformat(str(ts_raw).replace('Z', '+00:00')) if ts_raw else datetime.now(timezone.utc)
                message = SessionMessage(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    message_type=MessageType(msg_data.get("message_type", "user_input")),
                    emotion=EmotionType(msg_data.get("emotion", "neutral")) if msg_data.get("emotion") else None,
                    timestamp=ts,
                    metadata=msg_data.get("metadata", {})
                )
                messages.append(message)
            
            return APIResponse(
                success=True,
                data=messages,
                metadata={
                    "total": len(messages),
                    "session_id": session_id
                }
            )
            
        except Exception as e:
            log_therapy_event(
                event="session_messages_error",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to retrieve session messages",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("session_add_message")
    async def add_session_message(
        self, 
        user_id: str, 
        session_id: str,
        message: SessionMessage
    ) -> APIResponse[SessionMessage]:
        """Add a message to a therapy session."""
        await self._ensure_initialized()
        
        try:
            result = await self.supabase_client.save_memory_log(
                user_id=user_id,
                session_id=session_id,
                role=message.role,
                content=message.content,
                message_type=message.message_type,
                emotion=message.emotion,
                metadata=message.metadata
            )
            
            if not result.success:
                return APIResponse(
                    success=False,
                    error="Failed to save message",
                    error_code="MESSAGE_SAVE_FAILED"
                )
            
            return APIResponse(
                success=True,
                data=message,
                message="Message added successfully"
            )
            
        except Exception as e:
            log_therapy_event(
                event="session_add_message_error",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to add message",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("session_get_summary")
    async def get_session_summary(self, user_id: str, session_id: str) -> APIResponse[Dict[str, Any]]:
        """Get session summary with statistics."""
        await self._ensure_initialized()
        
        try:
            # Get session details
            session_result = await self.get_session(user_id, session_id)
            if not session_result.success:
                return session_result
            
            # Get message count
            messages_result = await self.supabase_client.client.table("memory_logs")\
                .select("count", count="exact")\
                .eq("user_id", user_id)\
                .eq("session_id", session_id)\
                .execute()
            
            # Get crisis events for this session
            crisis_result = await self.supabase_client.client.table("crisis_events")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("session_id", session_id)\
                .execute()
            
            session = session_result.data
            summary = {
                "session_id": session.session_id,
                "emotion": session.emotion.value,
                "crisis_level": session.crisis_level.value,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "message_count": messages_result.count if messages_result else 0,
                "crisis_events": len(crisis_result.data) if crisis_result else 0,
                "duration_minutes": None,
                "metadata": session.metadata
            }
            
            # Calculate duration if session ended
            if session.ended_at:
                duration = session.ended_at - session.created_at
                summary["duration_minutes"] = int(duration.total_seconds() / 60)
            
            return APIResponse(
                success=True,
                data=summary
            )
            
        except Exception as e:
            log_therapy_event(
                event="session_summary_error",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to generate session summary",
                error_code="INTERNAL_ERROR"
            )


# Global service instance
_session_service: Optional[SessionService] = None


async def get_session_service() -> SessionService:
    """Get initialized session service."""
    global _session_service
    
    if _session_service is None:
        _session_service = SessionService()
        await _session_service._ensure_initialized()
    
    return _session_service
