"""Session management service layer."""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import uuid

from src.database import get_supabase_client
from src.models import (
    TherapySession, SessionMessage, EmotionType, CrisisLevel,
    MessageType, APIResponse, PaginationParams, ProcessingStatus
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
            # Idempotency: return the most recent session if it was just created
            # within a short window to avoid duplicates from rapid repeated calls.
            idempotency_window_seconds = 45
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=idempotency_window_seconds)
            try:
                recent = (
                    self.supabase_client.client.table("therapy_sessions")
                    .select("*")
                    .eq("user_id", user_id)
                    .gte("created_at", cutoff.isoformat())
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if recent and getattr(recent, "data", None):
                    existing = self._build_session_from_data(recent.data[0])
                    log_therapy_event(
                        event="session_idempotent_return",
                        user_id=user_id, session_id=existing.id,
                        metadata={"window_seconds": idempotency_window_seconds}
                    )
                    return APIResponse(
                        success=True, data=existing,
                        message="Existing recent session returned"
                    )
            except Exception:
                # Non-fatal: fall back to creating a new session if the lookup fails
                pass

            session = TherapySession(
                user_id=user_id,
                emotion_detected=emotion or EmotionType.NEUTRAL,
                crisis_level=crisis_level or CrisisLevel.NONE,
                metadata=metadata or {},
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
            result = self.supabase_client.client.table("therapy_sessions")\
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
            
            session = self._build_session_from_data(result.data[0])
            
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
            
            result = query.execute()
            
            sessions = [self._build_session_from_data(data) for data in result.data]
            
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
            # Validate and normalize updates
            validation_result = self._validate_and_normalize_updates(updates)
            if not validation_result["valid"]:
                return APIResponse(
                    success=False,
                    error=validation_result["error"],
                    error_code="VALIDATION_ERROR"
                )
            
            normalized = validation_result["data"]

            # Update in database
            result = self.supabase_client.client.table("therapy_sessions")\
                .update(normalized)\
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
        pagination: Optional[PaginationParams] = None,
        *,
        after_created_at: Optional[str] = None,
        before_created_at: Optional[str] = None,
        order: str = "asc"
    ) -> APIResponse[List[SessionMessage]]:
        """Get messages for a therapy session."""
        await self._ensure_initialized()
        
        try:
            pagination = pagination or PaginationParams()

            # Prefer keyset pagination when cursor provided
            if after_created_at or before_created_at:
                result = await self.supabase_client.get_memory_logs_keyset(
                    user_id=user_id,
                    session_id=session_id,
                    limit=pagination.limit,
                    order=order,
                    after_created_at=after_created_at,
                    before_created_at=before_created_at,
                )
            else:
                # Fallback to offset-based for initial loads
                result = await self.supabase_client.get_memory_logs(
                    user_id=user_id,
                    session_id=session_id,
                    limit=pagination.limit,
                    offset=pagination.offset,
                    order="asc",
                )

            if not result.success:
                return APIResponse(
                    success=False,
                    error="Failed to retrieve session messages",
                    error_code="MESSAGES_FETCH_FAILED"
                )
            
            messages = [self._build_message_from_data(data) for data in result.data]
            
            # Build cursor metadata for client; avoid expensive count
            next_after = messages[-1].timestamp.isoformat() if messages else None
            prev_before = messages[0].timestamp.isoformat() if messages else None
            has_more = bool(messages)  # client can probe using next cursor

            return APIResponse(
                success=True,
                data=messages,
                metadata={
                    "total": len(messages),
                    "offset": pagination.offset,
                    "limit": pagination.limit,
                    "has_more": has_more,
                    "order": order,
                    "next_after": next_after,
                    "prev_before": prev_before,
                    "session_id": session_id,
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
            messages_result = self.supabase_client.client.table("memory_logs")\
                .select("count", count="exact")\
                .eq("user_id", user_id)\
                .eq("session_id", session_id)\
                .execute()
            
            # Get crisis events for this session
            crisis_result = self.supabase_client.client.table("crisis_events")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("session_id", session_id)\
                .execute()
            
            session = session_result.data
            summary = {
                "session_id": session.id,
                "emotion": session.emotion_detected.value if session.emotion_detected else None,
                "crisis_level": session.crisis_level.value if session.crisis_level else None,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "message_count": messages_result.count if messages_result else 0,
                "crisis_events": len(crisis_result.data) if crisis_result else 0,
                "duration_minutes": None,
                "metadata": session.metadata,
                "processing_status": session.processing_status.value if session.processing_status else None,
                "summary": session.summary,
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
    
    def _build_session_from_data(self, session_data: Dict[str, Any]) -> TherapySession:
        """Build TherapySession object from database data."""
        return TherapySession(
            id=session_data["session_id"],
            user_id=session_data["user_id"],
            emotion_detected=(
                EmotionType(session_data.get("emotion", "neutral")) 
                if session_data.get("emotion") else None
            ),
            crisis_level=(
                CrisisLevel(session_data.get("crisis_level", "none")) 
                if session_data.get("crisis_level") else None
            ),
            summary=session_data.get("session_summary"),
            metadata=session_data.get("metadata", {}),
            processing_status=ProcessingStatus(session_data.get("processing_status", "pending")),
            ended_at=(
                datetime.fromisoformat(str(session_data.get("ended_at")).replace('Z', '+00:00')) 
                if session_data.get("ended_at") else None
            ),
            created_at=datetime.fromisoformat(session_data["created_at"].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(session_data["updated_at"].replace('Z', '+00:00'))
        )
    
    def _build_message_from_data(self, msg_data: Dict[str, Any]) -> SessionMessage:
        """Build SessionMessage object from database data."""
        # Prefer 'timestamp' column from memory_logs, fallback to 'created_at'
        ts_raw = msg_data.get("timestamp") or msg_data.get("created_at")
        ts = (
            datetime.fromisoformat(str(ts_raw).replace('Z', '+00:00')) 
            if ts_raw else datetime.now(timezone.utc)
        )
        
        # Normalize message_type to match SessionMessage.pattern('^(user|assistant|system)$')
        raw_type = str(msg_data.get("message_type") or msg_data.get("role") or "user").lower()
        if raw_type in {"user_input", "user"}:
            norm_type = "user"
        elif raw_type in {"ai_response", "assistant"}:
            norm_type = "ai_response"
        elif raw_type in {"system", "system_message"}:
            norm_type = "system_message"
        else:
            # Fallback based on role field if present
            role_field = str(msg_data.get("role") or "user").lower()
            norm_type = role_field if role_field in {"user", "ai_response", "system_message"} else "user"

        # Map emotion to EmotionType if available
        emotion_val = msg_data.get("emotion")
        emotion_enum = EmotionType(emotion_val) if emotion_val else None

        # Build pydantic model with required fields
        return SessionMessage(
            session_id=msg_data.get("session_id"),
            user_id=msg_data.get("user_id"),
            content=msg_data["content"],
            message_type=norm_type,
            emotion_detected=emotion_enum,
            attack_detected=msg_data.get("attack_detected"),
            is_flagged=bool(msg_data.get("is_flagged", False)),
            processing_time_ms=msg_data.get("processing_time_ms"),
        )
    
    def _validate_and_normalize_updates(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize session update fields."""
        allowed_fields = {
            "emotion", "crisis_level", "processing_status",
            "session_summary", "metadata", "ended_at"
        }
        
        invalid_fields = set(updates.keys()) - allowed_fields
        if invalid_fields:
            return {
                "valid": False,
                "error": f"Invalid fields: {', '.join(invalid_fields)}"
            }
        
        normalized = {}
        for k, v in updates.items():
            if k == "emotion":
                normalized[k] = v.value if isinstance(v, EmotionType) else v
            elif k == "crisis_level":
                # Map NONE to NULL for DB constraint
                if isinstance(v, CrisisLevel):
                    normalized[k] = None if v == CrisisLevel.NONE else v.value
                else:
                    normalized[k] = None if str(v).lower() == "none" else v
            elif k == "processing_status":
                if isinstance(v, ProcessingStatus):
                    normalized[k] = v.value
                else:
                    try:
                        normalized[k] = ProcessingStatus(str(v)).value
                    except Exception:
                        return {
                            "valid": False,
                            "error": "Invalid processing_status"
                        }
            else:
                normalized[k] = v
        
        return {"valid": True, "data": normalized}


# Global service instance
_session_service: Optional[SessionService] = None


async def get_session_service() -> SessionService:
    """Get initialized session service."""
    global _session_service
    
    if _session_service is None:
        _session_service = SessionService()
        await _session_service._ensure_initialized()
    
    return _session_service
