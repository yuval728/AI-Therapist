"""User management API routes."""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.models import User, APIResponse, PaginationParams
from src.services import get_user_service
from src.api.middleware import get_current_user
from src.utils import log_therapy_event

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/profile")
async def get_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[User]:
    """Get current user's profile."""
    user_service = await get_user_service()
    user_id = current_user["user"]["id"]
    
    result = await user_service.get_user_profile(user_id)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error
        )
    
    return result


@router.put("/profile")
async def update_profile(
    updates: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[User]:
    """Update current user's profile."""
    user_service = await get_user_service()
    user_id = current_user["user"]["id"]
    
    result = await user_service.update_user_profile(user_id, updates)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result


@router.get("/preferences")
async def get_preferences(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """Get user preferences."""
    user_service = await get_user_service()
    user_id = current_user["user"]["id"]
    
    result = await user_service.get_user_preferences(user_id)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error
        )
    
    return result


@router.put("/preferences")
async def update_preferences(
    preferences: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """Update user preferences."""
    user_service = await get_user_service()
    user_id = current_user["user"]["id"]
    
    result = await user_service.update_user_preferences(user_id, preferences)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result


@router.get("/stats")
async def get_user_stats(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """Get user activity statistics."""
    user_service = await get_user_service()
    user_id = current_user["user"]["id"]
    
    result = await user_service.get_user_stats(user_id)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    return result


@router.delete("/account")
async def delete_account(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> APIResponse[None]:
    """Delete user account and all associated data."""
    user_service = await get_user_service()
    user_id = current_user["user"]["id"]
    
    result = await user_service.delete_user_account(user_id)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    return result
