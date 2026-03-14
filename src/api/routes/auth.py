"""Authentication API routes with enhanced security integration."""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request

from src.models import (
    SignInRequest, SignUpRequest, OAuthRequest, APIResponse
)
from src.services.auth_service import (
    sign_up as service_sign_up, 
    sign_in as service_sign_in, 
    sign_out as service_sign_out, 
    refresh_token as service_refresh_token,
    reset_password as service_reset_password, 
    oauth_sign_in as service_oauth_sign_in
)
from src.api.middleware import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check for forwarded IP first (proxy/load balancer)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    
    # Fall back to client host
    return request.client.host if request.client else "unknown"


@router.post("/signup")
async def signup_endpoint(request: SignUpRequest, req: Request) -> APIResponse[Dict[str, Any]]:
    """Register a new user account.
    
    Creates a new user account with email verification.
    Returns user profile information upon successful registration.
    """
    ip_address = get_client_ip(req)
    result = await service_sign_up(request, ip_address)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result


@router.post("/signin")
async def signin_endpoint(request: SignInRequest, req: Request) -> APIResponse[Dict[str, Any]]:
    """Authenticate user and create session.
    
    Validates credentials and returns access tokens for authenticated requests.
    """
    ip_address = get_client_ip(req)
    result = await service_sign_in(request, ip_address)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error
        )
    
    return result


@router.post("/oauth")
async def oauth_login(request: OAuthRequest, req: Request) -> APIResponse[Dict[str, Any]]:
    """Initiate OAuth authentication flow.
    
    Returns OAuth provider URL for authentication redirect.
    """
    ip_address = get_client_ip(req)
    result = await service_oauth_sign_in(request, ip_address)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result


@router.post("/signout")
async def signout_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)) -> APIResponse[None]:
    """Sign out current user and invalidate session."""
    result = await service_sign_out(current_user["user"]["id"])
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result


@router.post("/refresh")
async def refresh_token_endpoint(refresh_token: str) -> APIResponse[Dict[str, Any]]:
    """Refresh access token using refresh token."""
    result = await service_refresh_token(refresh_token)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error
        )
    
    return result


@router.get("/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)) -> APIResponse[Dict[str, Any]]:
    """Get current authenticated user information (optimized)."""
    # Return minimal user data needed for frontend authentication
    user_data = {
        "user": {
            "id": current_user["user"]["id"],
            "email": current_user["user"]["email"]
        }
    }
    
    return APIResponse(
        success=True,
        data=user_data,
        message="User information retrieved successfully"
    )


@router.get("/profile")
async def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)) -> APIResponse[Dict[str, Any]]:
    """Get current user's detailed profile information."""
    from src.services.auth_service import get_auth_service
    
    # Get the auth service and fetch full profile
    auth_service = await get_auth_service()
    user_id = current_user["user"]["id"]
    
    try:
        profile_result = await auth_service.supabase_client.get_user_profile(user_id)
        profile_data = profile_result.get("data", [{}])[0] if profile_result.get("success") else None
        
        return APIResponse(
            success=True,
            data={
                "user": current_user["user"],
                "profile": profile_data
            },
            message="User profile retrieved successfully"
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=f"Failed to fetch profile: {str(e)}"
        )


@router.post("/reset-password")
async def reset_password_endpoint(email: str) -> APIResponse[None]:
    """Send password reset email to user."""
    result = await service_reset_password(email)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )
    
    return result
