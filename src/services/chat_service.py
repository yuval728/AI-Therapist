"""Optimized chat service for therapy conversations."""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging

from src.models import (
    SessionMessage, EmotionType, APIResponse, PaginationParams
)
from src.services.session_service import get_session_service
from src.therapy.graphs.therapy_flow import build_therapy_graph
from src.utils import log_therapy_event, timing_decorator
from src.utils.rate_limiter import check_rate_limit

# Configure logger for this module
logger = logging.getLogger(__name__)


class ChatProcessingResult:
    """Data class for chat processing results."""
    def __init__(
        self,
        message_id: str,
        session_id: str,
        content: str,
        emotion: Optional[str] = None,
        crisis_level: Optional[str] = None,
        mode: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.message_id = message_id
        self.session_id = session_id
        self.content = content
        self.emotion = emotion
        self.crisis_level = crisis_level
        self.mode = mode
        self.processing_time_ms = processing_time_ms
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)


class StreamingChunk:
    """Data class for streaming response chunks."""
    def __init__(
        self,
        message_id: str,
        session_id: str,
        chunk: str,
        is_final: bool,
        emotion: Optional[str] = None,
        crisis_level: Optional[str] = None,
        mode: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.message_id = message_id
        self.session_id = session_id
        self.chunk = chunk
        self.is_final = is_final
        self.emotion = emotion
        self.crisis_level = crisis_level
        self.mode = mode
        self.timestamp = timestamp or datetime.now(timezone.utc)


class StreamingSession:
    """Data class for streaming session information."""
    def __init__(
        self,
        stream_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        content: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "initializing",
        chunks: Optional[List[StreamingChunk]] = None,
        start_time: Optional[datetime] = None,
        completion_time: Optional[datetime] = None,
        error: Optional[str] = None
    ):
        self.stream_id = stream_id
        self.user_id = user_id
        self.session_id = session_id
        self.content = content
        self.metadata = metadata or {}
        self.status = status
        self.chunks = chunks or []
        self.start_time = start_time or datetime.now(timezone.utc)
        self.completion_time = completion_time
        self.error = error


class TypingStatus:
    """Data class for typing status information."""
    def __init__(
        self,
        session_id: str,
        is_typing: bool,
        estimated_time_ms: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ):
        self.session_id = session_id
        self.is_typing = is_typing
        self.estimated_time_ms = estimated_time_ms
        self.timestamp = timestamp or datetime.now(timezone.utc)


class ChatService:
    """Optimized service for handling therapy chat functionality."""
    
    def __init__(self):
        self._active_processing: Dict[str, StreamingSession] = {}
        self._therapy_graphs_cache: Dict[str, Any] = {}
        self._session_service = None
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_old_processing_entries())
    
    async def _ensure_initialized(self):
        """Ensure service dependencies are initialized."""
        if not self._session_service:
            self._session_service = await get_session_service()
    
    async def _get_cached_therapy_graph(self, session_id: str):
        """Get therapy graph with optimized caching."""
        therapy_graph = self._therapy_graphs_cache.get(session_id)
        if not therapy_graph:
            therapy_graph = build_therapy_graph()
            self._therapy_graphs_cache[session_id] = therapy_graph
        return therapy_graph
    
    async def check_rate_limit(self, user_id: str, operation_type: str = "api_messages") -> Tuple[bool, Optional[int], Optional[int]]:
        """Check rate limit for user operations."""
        rate_key = f"chat_{operation_type}:{user_id}"
        rate_result = await check_rate_limit(rate_key, operation_type)
        return rate_result.allowed, rate_result.retry_after, rate_result.limit
    
    @timing_decorator("chat_process_message")
    async def process_chat_message(
        self,
        user_id: str,
        content: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> APIResponse[Any]:
        """Process a chat message and return AI response."""
        try:
            await self._ensure_initialized()
            
            # Handle session creation if needed
            if not session_id:
                session_result = await self._session_service.create_session(
                    user_id, 
                    metadata={"created_via": "chat_service"}
                )
                if not session_result.success:
                    logger.error(f"Failed to create session for user {user_id}")
                    return APIResponse(
                        success=False,
                        error="Failed to create chat session"
                    )
                session_id = session_result.data.id
            
            # Create user message
            user_message = SessionMessage(
                session_id=session_id,
                user_id=user_id,
                content=content,
                message_type="user",
                metadata=metadata or {}
            )
            
            # Save user message and process therapy response concurrently
            user_msg_task = asyncio.create_task(
                self._session_service.add_session_message(user_id, session_id, user_message)
            )
            
            # Get therapy graph and process message
            therapy_graph = await self._get_cached_therapy_graph(session_id)
            start_time = datetime.now(timezone.utc)
            
            initial_state = {
                "user_id": user_id,
                "session_id": session_id,
                "input": content,
                "messages": [],
                "emotion": "neutral",
                "crisis_level": "none",
                "mode": "chat",
                "response": "",
                "metadata": metadata or {}
            }
            
            therapy_task = asyncio.create_task(therapy_graph.ainvoke(initial_state))
            
            # Wait for both operations
            user_msg_result, therapy_result = await asyncio.gather(
                user_msg_task, therapy_task, return_exceptions=True
            )
            
            # Check results
            if isinstance(user_msg_result, Exception) or not user_msg_result.success:
                logger.error(f"Failed to save user message: {user_msg_result}")
                return APIResponse(
                    success=False,
                    error="Failed to save user message"
                )
            
            if isinstance(therapy_result, Exception):
                logger.exception(f"Therapy processing failed: {therapy_result}")
                return APIResponse(
                    success=False,
                    error="Failed to process message"
                )
            
            processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Create AI message
            ai_message = SessionMessage(
                session_id=session_id,
                user_id=user_id,
                content=therapy_result.get("response", ""),
                message_type="ai_response",
                emotion_detected=EmotionType(therapy_result.get("emotion", "neutral")),
                metadata={
                    **therapy_result.get("metadata", {}),
                    "processing_time_ms": processing_time,
                    "mode": therapy_result.get("mode", "chat"),
                    "crisis_level": therapy_result.get("crisis_level", "none")
                }
            )
            
            # Save AI message in background
            asyncio.create_task(
                self._session_service.add_session_message(user_id, session_id, ai_message)
            )
            
            # Log therapy interaction for analytics
            asyncio.create_task(
                log_therapy_event(
                    event="chat_interaction",
                    user_id=user_id,
                    session_id=session_id,
                    metadata={
                        "processing_time_ms": processing_time,
                        "emotion": therapy_result.get("emotion"),
                        "crisis_level": therapy_result.get("crisis_level"),
                        "mode": therapy_result.get("mode"),
                        "response_length": len(therapy_result.get("response", "")),
                    }
                )
            )
            
            # Return processing result
            result = ChatProcessingResult(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                content=therapy_result.get("response", ""),
                emotion=therapy_result.get("emotion"),
                crisis_level=therapy_result.get("crisis_level"),
                mode=therapy_result.get("mode"),
                processing_time_ms=processing_time,
                metadata=therapy_result.get("metadata", {}),
                timestamp=datetime.now(timezone.utc)
            )
            
            return APIResponse(
                success=True,
                data=result,
                message="Message processed successfully"
            )
            
        except Exception:
            logger.exception(f"Unexpected error in chat message processing for user {user_id}")
            return APIResponse(
                success=False,
                error="Internal server error during message processing"
            )
    
    async def start_streaming_chat(
        self,
        user_id: str,
        content: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> APIResponse[str]:
        """Start streaming chat response and return stream ID."""
        try:
            # Generate stream ID
            stream_id = str(uuid.uuid4())
            
            # Create streaming session
            streaming_session = StreamingSession(
                stream_id=stream_id,
                user_id=user_id,
                session_id=session_id,
                content=content,
                metadata=metadata or {},
                status="initializing"
            )
            
            # Store streaming session
            self._active_processing[stream_id] = streaming_session
            
            # Start background processing
            asyncio.create_task(self._process_streaming_message(stream_id))
            
            return APIResponse(
                success=True,
                data=stream_id,
                message="Streaming started"
            )
            
        except Exception:
            logger.exception(f"Failed to start streaming chat for user {user_id}")
            await log_therapy_event(
                event="streaming_start_error",
                user_id=user_id,
                error="Failed to start streaming chat"
            )
            return APIResponse(
                success=False,
                error="Failed to start streaming chat"
            )
    
    async def get_streaming_chunks(
        self,
        stream_id: str,
        user_id: str
    ) -> APIResponse[Any]:
        """Get streaming chunks for a chat response."""
        try:
            if stream_id not in self._active_processing:
                return APIResponse(
                    success=False,
                    error="Stream not found"
                )
            
            streaming_session = self._active_processing[stream_id]
            
            # Verify user ownership
            if streaming_session.user_id != user_id:
                return APIResponse(
                    success=False,
                    error="Access denied"
                )
            
            chunks = streaming_session.chunks
            
            # Clean up completed streams
            if streaming_session.status == "completed":
                # Keep for a short time to allow final polling
                if (streaming_session.completion_time and 
                    datetime.now(timezone.utc) - streaming_session.completion_time > timedelta(minutes=5)):
                    del self._active_processing[stream_id]
            
            return APIResponse(
                success=True,
                data=chunks,
                metadata={
                    "status": streaming_session.status,
                    "total_chunks": len(chunks),
                    "error": streaming_session.error
                }
            )
            
        except Exception:
            logger.exception(f"Error retrieving streaming chunks for stream {stream_id}")
            return APIResponse(
                success=False,
                error="Failed to retrieve streaming chunks"
            )
    
    async def get_typing_status(
        self,
        session_id: str,
        user_id: str
    ) -> APIResponse[Any]:
        """Get typing status for a session."""
        try:
            # Check if there's active processing for this session
            is_typing = False
            estimated_time = None
            
            for streaming_session in self._active_processing.values():
                if (streaming_session.session_id == session_id and 
                    streaming_session.user_id == user_id and
                    streaming_session.status in ["initializing", "processing"]):
                    is_typing = True
                    # Estimate remaining time based on elapsed time
                    elapsed = (datetime.now(timezone.utc) - streaming_session.start_time).total_seconds() * 1000
                    estimated_time = max(2000 - elapsed, 500)  # Estimate 2-3 seconds total
                    break
            
            status = TypingStatus(
                session_id=session_id,
                is_typing=is_typing,
                estimated_time_ms=int(estimated_time) if estimated_time else None
            )
            
            return APIResponse(
                success=True,
                data=status
            )
            
        except Exception:
            logger.exception(f"Error getting typing status for session {session_id}")
            return APIResponse(
                success=False,
                error="Failed to get typing status"
            )
    
    async def get_chat_history(
        self,
        user_id: str,
        session_id: str,
        offset: int = 0,
        limit: int = 50,
        order: str = "asc",
        after_timestamp: Optional[str] = None,
        before_timestamp: Optional[str] = None
    ) -> APIResponse[List[SessionMessage]]:
        """Get chat history for a session with optimized pagination."""
        try:
            await self._ensure_initialized()
            
            # Use keyset pagination if timestamps provided, otherwise offset-based
            if after_timestamp or before_timestamp:
                result = await self._session_service.get_session_messages(
                    user_id=user_id,
                    session_id=session_id,
                    pagination=PaginationParams(limit=limit),
                    after_created_at=after_timestamp,
                    before_created_at=before_timestamp,
                    order=order
                )
            else:
                result = await self._session_service.get_session_messages(
                    user_id=user_id,
                    session_id=session_id,
                    pagination=PaginationParams(offset=offset, limit=limit)
                )
            
            if not result.success:
                return APIResponse(
                    success=False,
                    error=result.error
                )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error retrieving chat history for session {session_id}")
            await log_therapy_event(
                event="chat_history_error",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Failed to retrieve chat history"
            )
    
    async def _process_streaming_message(self, stream_id: str):
        """Background task to process streaming message."""
        try:
            if stream_id not in self._active_processing:
                return
            
            streaming_session = self._active_processing[stream_id]
            streaming_session.status = "processing"
            
            await self._ensure_initialized()
            
            # Handle session creation if needed
            session_id = streaming_session.session_id
            if not session_id:
                session_result = await self._session_service.create_session(
                    streaming_session.user_id,
                    metadata={"created_via": "streaming_chat"}
                )
                if not session_result.success:
                    streaming_session.status = "error"
                    streaming_session.error = "Failed to create session"
                    return
                session_id = session_result.data.id
                streaming_session.session_id = session_id
            
            # Process through therapy flow
            therapy_graph = await self._get_cached_therapy_graph(session_id)
            
            initial_state = {
                "user_id": streaming_session.user_id,
                "session_id": session_id,
                "input": streaming_session.content,
                "messages": [],
                "emotion": "neutral",
                "crisis_level": "none",
                "mode": "chat",
                "response": "",
                "metadata": streaming_session.metadata
            }
            
            result = await therapy_graph.ainvoke(initial_state)
            response_text = result.get("response", "")
            
            # Simulate streaming by breaking response into chunks
            words = response_text.split()
            chunk_size = 3  # Words per chunk
            message_id = str(uuid.uuid4())
            
            for i in range(0, len(words), chunk_size):
                chunk_text = " ".join(words[i:i + chunk_size])
                is_final = i + chunk_size >= len(words)
                
                chunk = StreamingChunk(
                    message_id=message_id,
                    session_id=session_id,
                    chunk=chunk_text,
                    is_final=is_final,
                    emotion=result.get("emotion") if is_final else None,
                    crisis_level=result.get("crisis_level") if is_final else None,
                    mode=result.get("mode") if is_final else None
                )
                
                streaming_session.chunks.append(chunk)
                
                # Small delay between chunks for streaming effect
                await asyncio.sleep(0.1)
            
            # Save messages
            user_message = SessionMessage(
                session_id=session_id,
                user_id=streaming_session.user_id,
                content=streaming_session.content,
                message_type="user",
                metadata=streaming_session.metadata
            )
            
            ai_message = SessionMessage(
                session_id=session_id,
                user_id=streaming_session.user_id,
                content=response_text,
                message_type="ai_response",
                emotion_detected=EmotionType(result.get("emotion", "neutral")),
                metadata=result.get("metadata", {})
            )
            
            await self._session_service.add_session_message(streaming_session.user_id, session_id, user_message)
            await self._session_service.add_session_message(streaming_session.user_id, session_id, ai_message)
            
            # Mark as completed
            streaming_session.status = "completed"
            streaming_session.completion_time = datetime.now(timezone.utc)
            
            await log_therapy_event(
                event="streaming_chat_completed",
                user_id=streaming_session.user_id,
                session_id=session_id,
                message_id=message_id,
                chunks_count=len(streaming_session.chunks)
            )
            
        except Exception as e:
            logger.exception(f"Error processing streaming message for stream {stream_id}")
            if stream_id in self._active_processing:
                self._active_processing[stream_id].status = "error"
                self._active_processing[stream_id].error = str(e)
            
            await log_therapy_event(
                event="streaming_processing_error",
                stream_id=stream_id,
                error=str(e)
            )
    
    async def _cleanup_old_processing_entries(self):
        """Cleanup old processing entries periodically."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                current_time = datetime.now(timezone.utc)
                
                # Remove entries older than 30 minutes
                to_remove = []
                for stream_id, streaming_session in self._active_processing.items():
                    age = current_time - streaming_session.start_time
                    if age.total_seconds() > 1800:  # 30 minutes
                        to_remove.append(stream_id)
                
                for stream_id in to_remove:
                    del self._active_processing[stream_id]
                    
                # Cleanup old therapy graphs
                if len(self._therapy_graphs_cache) > 100:  # Keep only 100 most recent
                    # Remove oldest entries (simple cleanup, consider LRU for production)
                    items = list(self._therapy_graphs_cache.items())
                    for session_id, _ in items[:len(items) - 100]:
                        del self._therapy_graphs_cache[session_id]
                        
            except Exception as e:
                await log_therapy_event(
                    event="chat_cleanup_error",
                    error=str(e)
                )


# Service factory and singleton management
_chat_service_instance: Optional[ChatService] = None


async def get_chat_service() -> ChatService:
    """Get or create ChatService instance."""
    global _chat_service_instance
    
    if _chat_service_instance is None:
        _chat_service_instance = ChatService()
    
    return _chat_service_instance