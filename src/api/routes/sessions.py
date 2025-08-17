"""Therapy session API routes."""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.models import (
    TherapySession, SessionMessage, EmotionType, CrisisLevel,
    MessageType, APIResponse, PaginationParams
)
from src.services import get_session_service
from src.api.middleware import get_current_user
from src.utils import log_therapy_event

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/")
async def create_session(
    emotion: Optional[EmotionType] = None,
    crisis_level: Optional[CrisisLevel] = None,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[TherapySession]:
    """Create a new therapy session."""
    session_service = await get_session_service()
    user_id = current_user["user"]["id"]
    
    result = await session_service.create_session(
        user_id=user_id,
        emotion=emotion,
        crisis_level=crisis_level,
        metadata=metadata
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result


@router.get("/")
async def list_sessions(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[List[TherapySession]]:
    """List user's therapy sessions."""
    session_service = await get_session_service()
    user_id = current_user["user"]["id"]
    
    pagination = PaginationParams(offset=offset, limit=limit)
    result = await session_service.list_user_sessions(user_id, pagination)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    return result


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[TherapySession]:
    """Get specific therapy session."""
    session_service = await get_session_service()
    user_id = current_user["user"]["id"]
    
    result = await session_service.get_session(user_id, session_id)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error
        )
    
    return result


@router.put("/{session_id}")
async def update_session(
    session_id: str,
    updates: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[TherapySession]:
    """Update therapy session."""
    session_service = await get_session_service()
    user_id = current_user["user"]["id"]
    
    result = await session_service.update_session(user_id, session_id, updates)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result


@router.post("/{session_id}/end")
async def end_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[TherapySession]:
    """End a therapy session."""
    session_service = await get_session_service()
    user_id = current_user["user"]["id"]
    
    result = await session_service.end_session(user_id, session_id)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[List[SessionMessage]]:
    """Get messages for a therapy session."""
    session_service = await get_session_service()
    user_id = current_user["user"]["id"]
    
    pagination = PaginationParams(offset=offset, limit=limit)
    result = await session_service.get_session_messages(user_id, session_id, pagination)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error
        )
    
    return result


@router.post("/{session_id}/messages")
async def add_session_message(
    session_id: str,
    message: SessionMessage,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[SessionMessage]:
    """Add a message to a therapy session."""
    session_service = await get_session_service()
    user_id = current_user["user"]["id"]
    
    result = await session_service.add_session_message(user_id, session_id, message)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result


@router.get("/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """Get session summary with statistics."""
    session_service = await get_session_service()
    user_id = current_user["user"]["id"]
    
    result = await session_service.get_session_summary(user_id, session_id)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error
        )
    
    return result
