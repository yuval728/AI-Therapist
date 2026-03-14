"""Session management service layer."""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import logging

from src.database import get_supabase_client
from src.models import (
    TherapySession, SessionMessage, EmotionType, CrisisLevel,
    APIResponse, PaginationParams, ProcessingStatus
)
from src.utils import log_therapy_event, timing_decorator

# Configure logger for this module
logger = logging.getLogger(__name__)

class SessionService:
    """Optimized business logic for therapy session management."""
    
    def __init__(self):
        self.supabase_client = None
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 300  # 5 minutes
    
    async def _ensure_initialized(self):
        """Ensure database client is initialized."""
        if self.supabase_client is None:
            self.supabase_client = await get_supabase_client()
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache:
            return False
        return (datetime.now(timezone.utc) - self._cache[key]['timestamp']).total_seconds() < self._cache_ttl
    
    def _get_from_cache(self, key: str) -> Any:
        """Get value from cache if valid."""
        if self._is_cache_valid(key):
            return self._cache[key]['data']
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Set value in cache with timestamp."""
        self._cache[key] = {
            'data': data,
            'timestamp': datetime.now(timezone.utc)
        }
    
    @timing_decorator("session_create")
    async def create_session(
        self, 
        user_id: str, 
        emotion: Optional[EmotionType] = None,
        crisis_level: Optional[CrisisLevel] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> APIResponse[TherapySession]:
        """Create a new therapy session with improved efficiency."""
        await self._ensure_initialized()
        
        try:
            # Check for recent sessions to avoid duplicates (optimized query)
            cache_key = f"recent_session_{user_id}"
            recent_session = self._get_from_cache(cache_key)
            
            if not recent_session:
                # Only query DB if not in cache
                cutoff = datetime.now(timezone.utc) - timedelta(seconds=45)
                result = (
                    self.supabase_client.client.table("therapy_sessions")
                    .select("session_id,user_id,created_at,updated_at,emotion,crisis_level,metadata")
                    .eq("user_id", user_id)
                    .gte("created_at", cutoff.isoformat())
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                
                if result.data:
                    recent_session = self._build_session_from_data(result.data[0])
                    self._set_cache(cache_key, recent_session)
                    
                    logger.info(f"Returning recent session for user {user_id}")
                    return APIResponse(
                        success=True, 
                        data=recent_session,
                        message="Existing recent session returned"
                    )

            # Create new session
            session = TherapySession(
                user_id=user_id,
                emotion_detected=emotion or EmotionType.NEUTRAL,
                crisis_level=crisis_level or CrisisLevel.NONE,
                metadata=metadata or {},
            )
            
            result = await self.supabase_client.create_therapy_session(session)
            
            if not result:
                logger.error(f"Failed to create session for user {user_id}")
                return APIResponse(
                    success=False,
                    error="Failed to create therapy session",
                    error_code="SESSION_CREATE_FAILED"
                )
            
            # Cache the new session
            self._set_cache(cache_key, session)
            
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
            
        except Exception:
            logger.exception(f"Error creating session for user {user_id}")
            return APIResponse(
                success=False,
                error="Failed to create therapy session",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("session_get")
    async def get_session(self, user_id: str, session_id: str) -> APIResponse[TherapySession]:
        """Get therapy session by ID with caching."""
        await self._ensure_initialized()
        
        try:
            # Check cache first
            cache_key = f"session_{session_id}"
            cached_session = self._get_from_cache(cache_key)
            if cached_session:
                return APIResponse(success=True, data=cached_session)
            
            # Query database with only needed fields for better performance
            result = self.supabase_client.client.table("therapy_sessions")\
                .select("session_id,user_id,created_at,updated_at,emotion,crisis_level,processing_status,session_summary,metadata")\
                .eq("user_id", user_id)\
                .eq("session_id", session_id)\
                .single()\
                .execute()
            
            if not result.data:
                return APIResponse(
                    success=False,
                    error="Session not found",
                    error_code="SESSION_NOT_FOUND"
                )
            
            session = self._build_session_from_data(result.data)
            
            # Cache the result
            self._set_cache(cache_key, session)
            
            return APIResponse(success=True, data=session)
            
        except Exception:
            logger.exception(f"Error retrieving session {session_id} for user {user_id}")
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
            # Get current session to preserve existing metadata
            current_session = await self.get_session(user_id, session_id)
            if not current_session.success:
                return current_session
            
            # Merge new end session data with existing metadata
            existing_metadata = current_session.data.metadata or {}
            end_time = datetime.now(timezone.utc).isoformat()
            
            updated_metadata = {
                **existing_metadata,
                "session_ended": True,
                "ended_at": end_time
            }
            
            updates = {
                "updated_at": end_time,
                "metadata": updated_metadata
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
        """Get messages for a therapy session with optimized caching."""
        await self._ensure_initialized()
        
        try:
            pagination = pagination or PaginationParams()
            
            # Create cache key based on parameters
            cache_key = f"messages_{session_id}_{order}_{pagination.limit}_{pagination.offset}"
            if after_created_at:
                cache_key += f"_after_{after_created_at}"
            if before_created_at:
                cache_key += f"_before_{before_created_at}"
            
            # Check cache for frequently accessed message lists
            cached_messages = self._get_from_cache(cache_key)
            if cached_messages and not after_created_at and not before_created_at:
                return APIResponse(success=True, data=cached_messages)

            # Use optimized query strategy
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
                result = await self.supabase_client.get_memory_logs(
                    user_id=user_id,
                    session_id=session_id,
                    limit=pagination.limit,
                    offset=pagination.offset,
                    order=order,
                )

            # result is a list of dictionaries, not an APIResponse
            if not result:
                logger.warning(f"No messages found for session {session_id}")
                return APIResponse(
                    success=True,
                    data=[],
                    metadata={
                        "count": 0,
                        "order": order,
                        "has_more": False
                    }
                )
            
            # Build messages efficiently
            messages = [self._build_message_from_data(data) for data in result]
            
            # Cache result for future requests (only for standard queries)
            if not after_created_at and not before_created_at:
                self._set_cache(cache_key, messages)
            
            # Build efficient cursor metadata
            metadata = {
                "count": len(messages),
                "order": order,
                "has_more": len(messages) == pagination.limit
            }
            
            if messages:
                metadata["next_cursor"] = messages[-1].timestamp.isoformat()
                metadata["prev_cursor"] = messages[0].timestamp.isoformat()
            
            return APIResponse(
                success=True,
                data=messages,
                metadata=metadata
            )
            
        except Exception:
            logger.exception(f"Error retrieving messages for session {session_id}")
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
        """Add a message to a therapy session with cache invalidation."""
        await self._ensure_initialized()
        
        try:
            result = await self.supabase_client.save_memory_log(
                user_id=user_id,
                session_id=session_id,
                role=message.message_type,  # Use message_type as role
                content=message.content,
                message_type=message.message_type,
                emotion=message.emotion_detected,  # Use emotion_detected
                metadata={}  # SessionMessage doesn't have metadata field
            )
            
            if not result:
                logger.error(f"Failed to save message for session {session_id}")
                return APIResponse(
                    success=False,
                    error="Failed to save message",
                    error_code="MESSAGE_SAVE_FAILED"
                )
            
            # Invalidate relevant caches when new message is added
            cache_keys_to_invalidate = [
                f"messages_{session_id}_asc_{limit}_{offset}"
                for limit in [10, 20, 50] for offset in [0, 10, 20]
            ]
            for key in cache_keys_to_invalidate:
                if key in self._cache:
                    del self._cache[key]
            
            return APIResponse(
                success=True,
                data=message,
                message="Message added successfully"
            )
            
        except Exception:
            logger.exception(f"Error adding message to session {session_id}")
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

            # Use a single query to get message count and crisis events count efficiently
            # This avoids multiple round trips to the database
            async def get_counts():
                # Get message count (approximate is fine for summaries)
                messages_future = self.supabase_client.client.table("memory_logs")\
                    .select("id", count="estimated")\
                    .eq("user_id", user_id)\
                    .eq("session_id", session_id)\
                    .execute()
                
                # Get crisis events count
                crisis_future = self.supabase_client.client.table("crisis_events")\
                    .select("id", count="exact")\
                    .eq("user_id", user_id)\
                    .eq("session_id", session_id)\
                    .execute()
                
                return messages_future, crisis_future
            
            messages_result, crisis_result = await get_counts()
            
            session = session_result.data
            summary = {
                "session_id": session.id,
                "emotion": session.emotion_detected.value if session.emotion_detected else None,
                "crisis_level": session.crisis_level.value if session.crisis_level else None,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "message_count": messages_result.count if messages_result else 0,
                "crisis_events": crisis_result.count if crisis_result else 0,
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
        metadata = session_data.get("metadata", {})
        
        # Check if session was ended (stored in metadata since ended_at column doesn't exist)
        ended_at = None
        if metadata.get("session_ended") and metadata.get("ended_at"):
            try:
                ended_at = datetime.fromisoformat(str(metadata["ended_at"]).replace('Z', '+00:00'))
            except (ValueError, TypeError):
                ended_at = None
        
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
            metadata=metadata,
            processing_status=ProcessingStatus(session_data.get("processing_status", "pending")),
            ended_at=ended_at,
            created_at=datetime.fromisoformat(session_data["created_at"].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(session_data["updated_at"].replace('Z', '+00:00'))
        )
    
    def _build_message_from_data(self, msg_data: Dict[str, Any]) -> SessionMessage:
        """Build SessionMessage object from database data."""
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
            "session_summary", "metadata"
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
