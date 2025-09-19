"""REST API chat routes for therapy conversations."""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
import logging

from src.models import (
    SessionMessage, APIResponse, ChatMessageRequest, ChatMessageResponse, 
    TypingStatusResponse, StreamingChatResponse
)
from src.services import get_chat_service
from src.api.middleware import get_current_user
from src.utils import log_therapy_event

# Configure logger for this module
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send", response_model=APIResponse[ChatMessageResponse])
async def send_chat_message(
    message_request: ChatMessageRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[ChatMessageResponse]:
    """Send a chat message and get AI response."""
    user_id = current_user["user"]["id"]
    
    try:
        # Check rate limiting
        chat_service = await get_chat_service()
        allowed, retry_after, limit = await chat_service.check_rate_limit(user_id, "api_messages")
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after,
                    "limit": limit
                }
            )
        
        # Process the message through the chat service
        result = await chat_service.process_chat_message(
            user_id=user_id,
            content=message_request.content,
            session_id=message_request.session_id,
            metadata=message_request.metadata
        )
        
        if not result.success:
            if "Failed to create chat session" in result.error:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.error
                )
            elif "Failed to save user message" in result.error:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.error
                )
            elif "Failed to process message" in result.error:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.error
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error during message processing"
                )
        
        # Convert service result to API response format
        processing_result = result.data
        return APIResponse(
            success=True,
            data=ChatMessageResponse(
                message_id=processing_result.message_id,
                session_id=processing_result.session_id,
                content=processing_result.content,
                emotion=processing_result.emotion,
                crisis_level=processing_result.crisis_level,
                mode=processing_result.mode,
                processing_time_ms=processing_result.processing_time_ms,
                metadata=processing_result.metadata,
                timestamp=processing_result.timestamp
            ),
            message="Message processed successfully"
        )
        
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Unexpected error in chat message processing for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during message processing"
        )


@router.post("/stream", response_model=APIResponse[str])
async def start_streaming_chat(
    message_request: ChatMessageRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[str]:
    """Start streaming chat response and return a stream ID for polling."""
    user_id = current_user["user"]["id"]
    
    try:
        # Check rate limiting
        chat_service = await get_chat_service()
        allowed, retry_after, limit = await chat_service.check_rate_limit(user_id, "api_messages")
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds"
            )
        
        # Start streaming through chat service
        result = await chat_service.start_streaming_chat(
            user_id=user_id,
            content=message_request.content,
            session_id=message_request.session_id,
            metadata=message_request.metadata
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        await log_therapy_event(
            event="streaming_start_error",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start streaming chat"
        )


@router.get("/stream/{stream_id}", response_model=APIResponse[List[StreamingChatResponse]])
async def get_streaming_chunks(
    stream_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[List[StreamingChatResponse]]:
    """Get streaming chunks for a chat response."""
    user_id = current_user["user"]["id"]
    
    chat_service = await get_chat_service()
    result = await chat_service.get_streaming_chunks(stream_id, user_id)
    
    if not result.success:
        if "Stream not found" in result.error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.error
            )
        elif "Access denied" in result.error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
    
    # Convert service chunks to API response format
    api_chunks = []
    for chunk in result.data:
        api_chunks.append(StreamingChatResponse(
            message_id=chunk.message_id,
            session_id=chunk.session_id,
            chunk=chunk.chunk,
            is_final=chunk.is_final,
            emotion=chunk.emotion,
            crisis_level=chunk.crisis_level,
            mode=chunk.mode,
            timestamp=chunk.timestamp
        ))
    
    return APIResponse(
        success=True,
        data=api_chunks,
        metadata=result.metadata
    )


@router.get("/typing/{session_id}", response_model=APIResponse[TypingStatusResponse])
async def get_typing_status(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[TypingStatusResponse]:
    """Get typing status for a session."""
    user_id = current_user["user"]["id"]
    
    chat_service = await get_chat_service()
    result = await chat_service.get_typing_status(session_id, user_id)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    # Convert service result to API response format
    typing_status = result.data
    response = TypingStatusResponse(
        session_id=typing_status.session_id,
        is_typing=typing_status.is_typing,
        estimated_time_ms=typing_status.estimated_time_ms,
        timestamp=typing_status.timestamp
    )
    
    return APIResponse(
        success=True,
        data=response
    )


@router.get("/history/{session_id}", response_model=APIResponse[List[SessionMessage]])
async def get_chat_history(
    session_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    order: str = Query("asc", regex="^(asc|desc)$"),
    after_timestamp: Optional[str] = Query(None, description="Get messages after this timestamp"),
    before_timestamp: Optional[str] = Query(None, description="Get messages before this timestamp"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[List[SessionMessage]]:
    """Get chat history for a session with pagination."""
    user_id = current_user["user"]["id"]
    
    try:
        chat_service = await get_chat_service()
        result = await chat_service.get_chat_history(
            user_id=user_id,
            session_id=session_id,
            offset=offset,
            limit=limit,
            order=order,
            after_timestamp=after_timestamp,
            before_timestamp=before_timestamp
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.error
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        await log_therapy_event(
            event="chat_history_error",
            user_id=user_id,
            session_id=session_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )


# No additional background functions needed - all logic moved to ChatService