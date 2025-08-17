"""Authentication API routes."""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse

from src.models import (
    SignInRequest, SignUpRequest, OAuthRequest, UserProfile,
    APIResponse, ValidationError
)
from src.services import get_auth_service
from src.api.middleware import get_current_user, get_optional_user
from src.utils import log_therapy_event

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/signup")
async def sign_up(request: SignUpRequest) -> APIResponse[UserProfile]:
    """Register a new user account.
    
    Creates a new user account with email verification.
    Returns user profile information upon successful registration.
    """
    auth_service = await get_auth_service()
    result = await auth_service.sign_up(request)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result


@router.post("/signin")
async def sign_in(request: SignInRequest) -> APIResponse[Dict[str, Any]]:
    """Authenticate user and create session.
    
    Validates credentials and returns access tokens for authenticated requests.
    """
    auth_service = await get_auth_service()
    result = await auth_service.sign_in(request)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error
        )
    
    return result


@router.post("/oauth")
async def oauth_login(request: OAuthRequest) -> APIResponse[Dict[str, Any]]:
    """Initiate OAuth authentication flow.
    
    Returns OAuth provider URL for authentication redirect.
    """
    auth_service = await get_auth_service()
    result = await auth_service.oauth_sign_in(request)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result


@router.post("/signout")
async def sign_out(current_user: Dict[str, Any] = Depends(get_current_user)) -> APIResponse[None]:
    """Sign out current user and invalidate session."""
    auth_service = await get_auth_service()
    result = await auth_service.sign_out(current_user["user"]["id"])
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result


@router.post("/refresh")
async def refresh_token(refresh_token: str) -> APIResponse[Dict[str, Any]]:
    """Refresh access token using refresh token."""
    auth_service = await get_auth_service()
    result = await auth_service.refresh_token(refresh_token)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error
        )
    
    return result


@router.get("/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)) -> APIResponse[Dict[str, Any]]:
    """Get current authenticated user information."""
    return APIResponse(
        success=True,
        data=current_user,
        message="User information retrieved successfully"
    )


@router.post("/reset-password")
async def reset_password(email: str) -> APIResponse[None]:
    """Send password reset email to user."""
    auth_service = await get_auth_service()
    result = await auth_service.reset_password(email)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result
