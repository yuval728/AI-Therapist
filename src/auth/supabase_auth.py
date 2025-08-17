"""Supabase authentication integration for AI therapist."""
from typing import Dict, Optional, Any
from dataclasses import dataclass
import asyncio
from datetime import datetime, timezone

from src.database import get_supabase_client, supabase_session
from src.models import UserProfile, SignInRequest, SignUpRequest, OAuthRequest
from src.utils import log_therapy_event, timing_decorator, ValidationError
from src.config import get_settings


@dataclass
class AuthResult:
    """Authentication result structure."""
    success: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SupabaseAuth:
    """Enhanced Supabase authentication service."""
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase_client = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure Supabase client is initialized."""
        if not self._initialized:
            self.supabase_client = await get_supabase_client()
            self._initialized = True
    
    @timing_decorator("user_signup")
    async def sign_up(self, request: SignUpRequest) -> AuthResult:
        """Sign up new user with profile creation."""
        await self._ensure_initialized()
        
        try:
            # Sign up with Supabase Auth
            auth_response = self.supabase_client.client.auth.sign_up({
                "email": request.email,
                "password": request.password,
                "options": {
                    "data": {
                        "full_name": request.full_name,
                        "preferences": request.preferences or {}
                    }
                }
            })
            
            if auth_response.user is None:
                return AuthResult(
                    success=False,
                    error="Sign up failed - no user returned"
                )
            
            user_id = auth_response.user.id
            
            # Create user profile
            profile_result = await self.supabase_client.create_user_profile(
                user_id=user_id,
                full_name=request.full_name,
                email=request.email,
                preferences=request.preferences or {}
            )
            
            log_therapy_event(
                event="user_signup_completed",
                user_id=user_id,
                email=request.email,
                profile_created=profile_result.success
            )
            
            return AuthResult(
                success=True,
                user_id=user_id,
                email=request.email,
                access_token=auth_response.session.access_token if auth_response.session else None,
                refresh_token=auth_response.session.refresh_token if auth_response.session else None,
                metadata={"profile_created": profile_result.success}
            )
            
        except Exception as e:
            log_therapy_event(
                event="user_signup_failed",
                email=request.email,
                error=str(e)
            )
            return AuthResult(
                success=False,
                error=str(e)
            )
    
    @timing_decorator("user_signin")
    async def sign_in(self, request: SignInRequest) -> AuthResult:
        """Sign in existing user."""
        await self._ensure_initialized()
        
        try:
            auth_response = self.supabase_client.client.auth.sign_in_with_password({
                "email": request.email,
                "password": request.password
            })
            
            if auth_response.user is None:
                return AuthResult(
                    success=False,
                    error="Invalid email or password"
                )
            
            user_id = auth_response.user.id
            
            # Get user profile
            profile_result = await self.supabase_client.get_user_profile(user_id)
            
            log_therapy_event(
                event="user_signin_completed",
                user_id=user_id,
                email=request.email
            )
            
            return AuthResult(
                success=True,
                user_id=user_id,
                email=request.email,
                access_token=auth_response.session.access_token if auth_response.session else None,
                refresh_token=auth_response.session.refresh_token if auth_response.session else None,
                metadata={"profile_exists": profile_result.success}
            )
            
        except Exception as e:
            log_therapy_event(
                event="user_signin_failed",
                email=request.email,
                error=str(e)
            )
            return AuthResult(
                success=False,
                error=str(e)
            )
    
    @timing_decorator("oauth_signin")
    async def oauth_sign_in(self, request: OAuthRequest) -> AuthResult:
        """OAuth sign in with provider."""
        await self._ensure_initialized()
        
        try:
            auth_response = self.supabase_client.client.auth.sign_in_with_oauth({
                "provider": request.provider,
                "options": {
                    "redirect_to": request.redirect_url
                }
            })
            
            # OAuth typically returns a URL for redirection
            log_therapy_event(
                event="oauth_signin_initiated",
                provider=request.provider,
                redirect_url=request.redirect_url
            )
            
            return AuthResult(
                success=True,
                metadata={
                    "auth_url": auth_response.url if hasattr(auth_response, 'url') else None,
                    "provider": request.provider
                }
            )
            
        except Exception as e:
            log_therapy_event(
                event="oauth_signin_failed",
                provider=request.provider,
                error=str(e)
            )
            return AuthResult(
                success=False,
                error=str(e)
            )
    
    @timing_decorator("user_signout")
    async def sign_out(self, user_id: str) -> AuthResult:
        """Sign out user."""
        await self._ensure_initialized()
        
        try:
            self.supabase_client.client.auth.sign_out()
            
            log_therapy_event(
                event="user_signout_completed",
                user_id=user_id
            )
            
            return AuthResult(success=True)
            
        except Exception as e:
            log_therapy_event(
                event="user_signout_failed",
                user_id=user_id,
                error=str(e)
            )
            return AuthResult(
                success=False,
                error=str(e)
            )
    
    @timing_decorator("refresh_token")
    async def refresh_session(self, refresh_token: str) -> AuthResult:
        """Refresh user session."""
        await self._ensure_initialized()
        
        try:
            auth_response = self.supabase_client.client.auth.refresh_session(refresh_token)
            
            if auth_response.user is None:
                return AuthResult(
                    success=False,
                    error="Token refresh failed"
                )
            
            user_id = auth_response.user.id
            
            log_therapy_event(
                event="token_refresh_completed",
                user_id=user_id
            )
            
            return AuthResult(
                success=True,
                user_id=user_id,
                email=auth_response.user.email,
                access_token=auth_response.session.access_token if auth_response.session else None,
                refresh_token=auth_response.session.refresh_token if auth_response.session else None
            )
            
        except Exception as e:
            log_therapy_event(
                event="token_refresh_failed",
                error=str(e)
            )
            return AuthResult(
                success=False,
                error=str(e)
            )
    
    @timing_decorator("get_user")
    async def get_current_user(self, access_token: str) -> AuthResult:
        """Get current user from access token."""
        await self._ensure_initialized()
        
        try:
            # Set the session
            self.supabase_client.client.auth.set_session(access_token, "")
            
            user_response = self.supabase_client.client.auth.get_user(access_token)
            
            if user_response.user is None:
                return AuthResult(
                    success=False,
                    error="Invalid access token"
                )
            
            user_id = user_response.user.id
            
            # Get user profile
            profile_result = await self.supabase_client.get_user_profile(user_id)
            
            return AuthResult(
                success=True,
                user_id=user_id,
                email=user_response.user.email,
                metadata={
                    "profile": profile_result.data[0] if profile_result.success and profile_result.data else None
                }
            )
            
        except Exception as e:
            log_therapy_event(
                event="get_user_failed",
                error=str(e)
            )
            return AuthResult(
                success=False,
                error=str(e)
            )
    
    @timing_decorator("reset_password")
    async def reset_password(self, email: str) -> AuthResult:
        """Send password reset email."""
        await self._ensure_initialized()
        
        try:
            self.supabase_client.client.auth.reset_password_email(email)
            
            log_therapy_event(
                event="password_reset_sent",
                email=email
            )
            
            return AuthResult(success=True)
            
        except Exception as e:
            log_therapy_event(
                event="password_reset_failed",
                email=email,
                error=str(e)
            )
            return AuthResult(
                success=False,
                error=str(e)
            )
    
    @timing_decorator("update_password")
    async def update_password(self, user_id: str, new_password: str) -> AuthResult:
        """Update user password."""
        await self._ensure_initialized()
        
        try:
            auth_response = self.supabase_client.client.auth.update_user({
                "password": new_password
            })
            
            if auth_response.user is None:
                return AuthResult(
                    success=False,
                    error="Password update failed"
                )
            
            log_therapy_event(
                event="password_updated",
                user_id=user_id
            )
            
            return AuthResult(success=True, user_id=user_id)
            
        except Exception as e:
            log_therapy_event(
                event="password_update_failed",
                user_id=user_id,
                error=str(e)
            )
            return AuthResult(
                success=False,
                error=str(e)
            )
    
    @timing_decorator("update_profile")
    async def update_user_profile(
        self, 
        user_id: str, 
        updates: Dict[str, Any]
    ) -> AuthResult:
        """Update user profile."""
        await self._ensure_initialized()
        
        try:
            # Update auth metadata if needed
            auth_updates = {}
            if "full_name" in updates:
                auth_updates["data"] = {"full_name": updates["full_name"]}
            
            if auth_updates:
                self.supabase_client.client.auth.update_user(auth_updates)
            
            # Update profile table
            profile_result = await self.supabase_client.client.table("profiles").update(updates).eq("id", user_id).execute()
            
            if profile_result.error:
                return AuthResult(
                    success=False,
                    error=str(profile_result.error)
                )
            
            log_therapy_event(
                event="profile_updated",
                user_id=user_id,
                updated_fields=list(updates.keys())
            )
            
            return AuthResult(
                success=True,
                user_id=user_id,
                metadata={"updated_fields": list(updates.keys())}
            )
            
        except Exception as e:
            log_therapy_event(
                event="profile_update_failed",
                user_id=user_id,
                error=str(e)
            )
            return AuthResult(
                success=False,
                error=str(e)
            )


# Global auth service instance
_auth_service: Optional[SupabaseAuth] = None


async def get_auth_service() -> SupabaseAuth:
    """Get initialized auth service."""
    global _auth_service
    
    if _auth_service is None:
        _auth_service = SupabaseAuth()
        await _auth_service._ensure_initialized()
    
    return _auth_service
