"""Authentication service layer for business logic."""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from datetime import datetime, timezone

from src.auth import SupabaseAuth, AuthResult, get_auth_service as get_supabase_auth
from src.models import (
    SignUpRequest, SignInRequest, OAuthRequest, User,
    APIResponse
)
from src.utils import log_therapy_event, timing_decorator, ValidationError, validate_email_address, validate_password_strength      
from src.config import get_settings


class AuthService:
    """Business logic layer for authentication operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase_auth: Optional[SupabaseAuth] = None
    
    async def _ensure_initialized(self):
        """Ensure authentication service is initialized."""
        if self.supabase_auth is None:
            self.supabase_auth = await get_supabase_auth()
    
    @timing_decorator("auth_signup")
    async def sign_up(self, request: SignUpRequest) -> APIResponse[User]:
        """Handle user registration with validation."""
        await self._ensure_initialized()
        
        try:
            # Validate input
            if not validate_email_address(request.email):
                raise ValidationError("Invalid email format")
            
            if not validate_password_strength(request.password):
                raise ValidationError("Password does not meet security requirements")
            
            # Attempt signup
            auth_result = await self.supabase_auth.sign_up(request)
            print(auth_result)
            if not auth_result.success:
                log_therapy_event(
                    event="signup_failed",
                    email=request.email,
                    error=auth_result.error
                )
                return APIResponse(
                    success=False,
                    error=auth_result.error or "Registration failed",
                    error_code="SIGNUP_FAILED"
                )
            
            # Create user profile response
            user_profile = User(
                id=auth_result.user_id,
                email=auth_result.email,
                full_name=request.full_name,
                preferences={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            log_therapy_event(
                event="signup_success",
                user_id=auth_result.user_id,
                email=auth_result.email
            )
            
            return APIResponse(
                success=True,
                data=user_profile,
                message="Registration successful. Please check your email for verification."
            )
            
        except ValidationError as e:
            return APIResponse(
                success=False,
                error=str(e),
                error_code="VALIDATION_ERROR"
            )
        except Exception as e:
            log_therapy_event(
                event="signup_error",
                email=request.email,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="An unexpected error occurred during registration",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("auth_signin")
    async def sign_in(self, request: SignInRequest) -> APIResponse[Dict[str, Any]]:
        """Handle user login with session management."""
        await self._ensure_initialized()
        
        try:
            # Validate input
            if not validate_email_address(request.email):
                raise ValidationError("Invalid email format")
            
            # Attempt signin
            auth_result = await self.supabase_auth.sign_in(request)
            
            if not auth_result.success:
                log_therapy_event(
                    event="signin_failed",
                    email=request.email,
                    error=auth_result.error
                )
                return APIResponse(
                    success=False,
                    error=auth_result.error or "Invalid credentials",
                    error_code="SIGNIN_FAILED"
                )
            
            # Prepare response with tokens and user info
            response_data = {
                "user": {
                    "id": auth_result.user_id,
                    "email": auth_result.email
                },
                "tokens": {
                    "access_token": auth_result.access_token,
                    "refresh_token": auth_result.refresh_token,
                    "token_type": "bearer"
                },
                "profile": auth_result.metadata.get("profile") if auth_result.metadata else None
            }
            
            log_therapy_event(
                event="signin_success",
                user_id=auth_result.user_id,
                email=auth_result.email
            )
            
            return APIResponse(
                success=True,
                data=response_data,
                message="Login successful"
            )
            
        except ValidationError as e:
            return APIResponse(
                success=False,
                error=str(e),
                error_code="VALIDATION_ERROR"
            )
        except Exception as e:
            log_therapy_event(
                event="signin_error",
                email=request.email,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="An unexpected error occurred during login",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("auth_oauth")
    async def oauth_sign_in(self, request: OAuthRequest) -> APIResponse[Dict[str, Any]]:
        """Handle OAuth authentication."""
        await self._ensure_initialized()
        
        try:
            auth_result = await self.supabase_auth.oauth_sign_in(request)
            
            if not auth_result.success:
                return APIResponse(
                    success=False,
                    error=auth_result.error or "OAuth authentication failed",
                    error_code="OAUTH_FAILED"
                )
            
            return APIResponse(
                success=True,
                data=auth_result.metadata,
                message="OAuth URL generated successfully"
            )
            
        except Exception as e:
            log_therapy_event(
                event="oauth_error",
                provider=request.provider,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="OAuth authentication error",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("auth_signout")
    async def sign_out(self, user_id: str) -> APIResponse[None]:
        """Handle user logout."""
        await self._ensure_initialized()
        
        try:
            auth_result = await self.supabase_auth.sign_out(user_id)
            
            if not auth_result.success:
                return APIResponse(
                    success=False,
                    error=auth_result.error or "Logout failed",
                    error_code="SIGNOUT_FAILED"
                )
            
            return APIResponse(
                success=True,
                message="Logout successful"
            )
            
        except Exception as e:
            log_therapy_event(
                event="signout_error",
                user_id=user_id,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Logout error",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("auth_refresh")
    async def refresh_token(self, refresh_token: str) -> APIResponse[Dict[str, Any]]:
        """Handle token refresh."""
        await self._ensure_initialized()
        
        try:
            auth_result = await self.supabase_auth.refresh_session(refresh_token)
            
            if not auth_result.success:
                return APIResponse(
                    success=False,
                    error=auth_result.error or "Token refresh failed",
                    error_code="REFRESH_FAILED"
                )
            
            response_data = {
                "tokens": {
                    "access_token": auth_result.access_token,
                    "refresh_token": auth_result.refresh_token,
                    "token_type": "bearer"
                },
                "user": {
                    "id": auth_result.user_id,
                    "email": auth_result.email
                }
            }
            
            return APIResponse(
                success=True,
                data=response_data,
                message="Token refreshed successfully"
            )
            
        except Exception as e:
            log_therapy_event(
                event="refresh_error",
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Token refresh error",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("auth_get_user")
    async def get_current_user(self, access_token: str) -> APIResponse[Dict[str, Any]]:
        """Get current user from access token."""
        await self._ensure_initialized()
        
        try:
            auth_result = await self.supabase_auth.get_current_user(access_token)
            
            if not auth_result.success:
                return APIResponse(
                    success=False,
                    error=auth_result.error or "Invalid token",
                    error_code="INVALID_TOKEN"
                )
            
            response_data = {
                "user": {
                    "id": auth_result.user_id,
                    "email": auth_result.email
                },
                "profile": auth_result.metadata.get("profile") if auth_result.metadata else None
            }
            
            return APIResponse(
                success=True,
                data=response_data
            )
            
        except Exception as e:
            log_therapy_event(
                event="get_user_error",
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="User retrieval error",
                error_code="INTERNAL_ERROR"
            )
    
    @timing_decorator("auth_reset_password")
    async def reset_password(self, email: str) -> APIResponse[None]:
        """Handle password reset request."""
        await self._ensure_initialized()
        
        try:
            if not validate_email_address(email):
                raise ValidationError("Invalid email format")
            
            auth_result = await self.supabase_auth.reset_password(email)
            
            if not auth_result.success:
                return APIResponse(
                    success=False,
                    error=auth_result.error or "Password reset failed",
                    error_code="RESET_FAILED"
                )
            
            return APIResponse(
                success=True,
                message="Password reset email sent successfully"
            )
            
        except ValidationError as e:
            return APIResponse(
                success=False,
                error=str(e),
                error_code="VALIDATION_ERROR"
            )
        except Exception as e:
            log_therapy_event(
                event="reset_password_error",
                email=email,
                error=str(e)
            )
            return APIResponse(
                success=False,
                error="Password reset error",
                error_code="INTERNAL_ERROR"
            )


# Global service instance
_auth_service: Optional[AuthService] = None


async def get_auth_service() -> AuthService:
    """Get initialized auth service."""
    global _auth_service
    
    if _auth_service is None:
        _auth_service = AuthService()
        await _auth_service._ensure_initialized()
    
    return _auth_service
