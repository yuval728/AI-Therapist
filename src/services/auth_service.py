
from typing import Dict, Optional, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta

from src.database import get_supabase_client
from src.models import SignUpRequest, SignInRequest, OAuthRequest, APIResponse
from src.utils import log_therapy_event

# Security tracking
login_attempts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
failed_attempts: Dict[str, int] = defaultdict(int)
blocked_ips: Dict[str, datetime] = {}

# Security thresholds
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 minutes
RATE_LIMIT_WINDOW = 300  # 5 minutes


def check_brute_force_protection(identifier: str, ip_address: Optional[str] = None) -> bool:
    """Check if identifier or IP is under brute force protection."""
    now = datetime.utcnow()
    
    # Check IP blocking
    if ip_address and ip_address in blocked_ips:
        if (now - blocked_ips[ip_address]).seconds < LOCKOUT_DURATION:
            return False
        else:
            del blocked_ips[ip_address]
    
    # Check failed attempts
    if failed_attempts[identifier] >= MAX_LOGIN_ATTEMPTS:
        return False
    
    return True


def record_login_attempt(identifier: str, success: bool, ip_address: Optional[str] = None):
    """Record login attempt for security monitoring."""
    now = datetime.utcnow()
    
    # Clean old attempts
    attempts = login_attempts[identifier]
    cutoff = now - timedelta(seconds=RATE_LIMIT_WINDOW)
    while attempts and attempts[0]['timestamp'] < cutoff:
        attempts.popleft()
    
    # Record new attempt
    attempts.append({
        'timestamp': now,
        'success': success,
        'ip_address': ip_address
    })
    
    if not success:
        failed_attempts[identifier] += 1
        
        # Block IP after multiple failures
        if ip_address and failed_attempts[identifier] >= MAX_LOGIN_ATTEMPTS:
            blocked_ips[ip_address] = now
    else:
        # Reset failed attempts on success
        failed_attempts[identifier] = 0


class AuthService:
    """Enhanced authentication service using Supabase with security hardening."""
    
    def __init__(self):
        self.supabase_client = None
        self._initialized = False
        self.session_tokens = {}  # Track active sessions
    
    async def _ensure_initialized(self):
        """Ensure Supabase client is initialized."""
        if not self._initialized:
            self.supabase_client = await get_supabase_client()
            self._initialized = True
    
    async def sign_up(self, request: SignUpRequest, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Enhanced sign up with security validation."""
        await self._ensure_initialized()
        
        identifier = request.email.lower()
        
        try:
            # Check brute force protection
            if not check_brute_force_protection(identifier, ip_address):
                record_login_attempt(identifier, False, ip_address)
                return {"success": False, "error": "Account temporarily locked due to multiple failed attempts"}
            
            # Enhanced email validation
            from src.utils.validation import validate_email_address, validate_password_strength
            email_result = await validate_email_address(request.email, identifier)
            if not email_result.is_valid:
                return {"success": False, "error": "Invalid email format"}
            
            # Enhanced password validation
            password_result = await validate_password_strength(request.password, identifier)
            if not password_result.is_valid:
                return {"success": False, "error": "Password does not meet security requirements"}
            
            # Sign up with Supabase Auth
            auth_response = self.supabase_client.client.auth.sign_up({
                "email": email_result.sanitized_content,
                "password": request.password,
                "options": {
                    "data": {
                        "full_name": request.full_name
                    }
                }
            })
            
            if auth_response.user is None:
                record_login_attempt(identifier, False, ip_address)
                return {"success": False, "error": "Sign up failed - no user returned"}
            
            user_id = auth_response.user.id
            
            # Create user profile
            profile_result = await self.supabase_client.create_user_profile(
                user_id=user_id,
                full_name=request.full_name,
                email=email_result.sanitized_content,
                preferences={}
            )

            if not profile_result:
                log_therapy_event(
                    event="user_signup_failed",
                    email=email_result.sanitized_content,
                    user_id=user_id,
                    error="Profile creation failed",
                    ip_address=ip_address
                )
                return {"success": False, "error": "Profile creation failed"}

            # Record successful signup
            record_login_attempt(identifier, True, ip_address)
            
            log_therapy_event(
                event="user_signup_completed",
                user_id=user_id,
                email=email_result.sanitized_content,
                ip_address=ip_address,
                security_score=min(email_result.security_score, password_result.security_score)
            )

            return {
                "success": True,
                "user_id": user_id,
                "email": email_result.sanitized_content,
                "access_token": auth_response.session.access_token if auth_response.session else None,
                "refresh_token": auth_response.session.refresh_token if auth_response.session else None
            }
            
        except Exception as e:
            record_login_attempt(identifier, False, ip_address)
            log_therapy_event(
                event="user_signup_failed",
                email=request.email,
                error=str(e),
                ip_address=ip_address
            )
            return {"success": False, "error": str(e)}
    
    async def sign_in(self, request: SignInRequest, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Enhanced sign in with security monitoring."""
        await self._ensure_initialized()
        
        identifier = request.email.lower()
        
        try:
            # Check brute force protection
            if not check_brute_force_protection(identifier, ip_address):
                record_login_attempt(identifier, False, ip_address)
                return {"success": False, "error": "Account temporarily locked due to multiple failed attempts"}
            
            # Enhanced email validation
            from src.utils.validation import validate_email_address
            email_result = await validate_email_address(request.email, identifier)
            if not email_result.is_valid:
                record_login_attempt(identifier, False, ip_address)
                return {"success": False, "error": "Invalid email format"}
            
            auth_response = self.supabase_client.client.auth.sign_in_with_password({
                "email": email_result.sanitized_content,
                "password": request.password
            })
            
            if auth_response.user is None:
                record_login_attempt(identifier, False, ip_address)
                log_therapy_event(
                    event="user_signin_failed",
                    email=email_result.sanitized_content,
                    error="Invalid credentials",
                    ip_address=ip_address
                )
                return {"success": False, "error": "Invalid email or password"}
            
            user_id = auth_response.user.id
            
            # Get user profile
            profile_result = await self.supabase_client.get_user_profile(user_id)
            
            # Record successful login
            record_login_attempt(identifier, True, ip_address)
            
            log_therapy_event(
                event="user_signin_completed",
                user_id=user_id,
                email=email_result.sanitized_content,
                ip_address=ip_address,
                security_score=email_result.security_score
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "email": email_result.sanitized_content,
                "access_token": auth_response.session.access_token if auth_response.session else None,
                "refresh_token": auth_response.session.refresh_token if auth_response.session else None,
                "profile": profile_result.get("data", [{}])[0] if profile_result.get("success") else None
            }
            
        except Exception as e:
            record_login_attempt(identifier, False, ip_address)
            log_therapy_event(
                event="user_signin_failed",
                email=request.email,
                error=str(e),
                ip_address=ip_address
            )
            return {"success": False, "error": str(e)}
    
    async def oauth_sign_in(self, request: OAuthRequest) -> Dict[str, Any]:
        """OAuth sign in with provider."""
        await self._ensure_initialized()
        
        try:
            auth_response = self.supabase_client.client.auth.sign_in_with_oauth({
                "provider": request.provider,
                "options": {
                    "redirect_to": request.redirect_url
                }
            })
            
            log_therapy_event(
                event="oauth_signin_initiated",
                provider=request.provider,
                redirect_url=request.redirect_url
            )
            
            return {
                "success": True,
                "auth_url": auth_response.url if hasattr(auth_response, 'url') else None,
                "provider": request.provider
            }
            
        except Exception as e:
            log_therapy_event(
                event="oauth_signin_failed",
                provider=request.provider,
                error=str(e)
            )
            return {"success": False, "error": str(e)}
    
    async def sign_out(self, user_id: str) -> Dict[str, Any]:
        """Sign out user."""
        await self._ensure_initialized()
        
        try:
            self.supabase_client.client.auth.sign_out()
            
            log_therapy_event(
                event="user_signout_completed",
                user_id=user_id
            )
            
            return {"success": True}
            
        except Exception as e:
            log_therapy_event(
                event="user_signout_failed",
                user_id=user_id,
                error=str(e)
            )
            return {"success": False, "error": str(e)}
    
    async def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh user session."""
        await self._ensure_initialized()
        
        try:
            auth_response = self.supabase_client.client.auth.refresh_session(refresh_token)
            
            if auth_response.user is None:
                return {"success": False, "error": "Token refresh failed"}
            
            user_id = auth_response.user.id
            
            log_therapy_event(
                event="token_refresh_completed",
                user_id=user_id
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "email": auth_response.user.email,
                "access_token": auth_response.session.access_token if auth_response.session else None,
                "refresh_token": auth_response.session.refresh_token if auth_response.session else None
            }
            
        except Exception as e:
            log_therapy_event(
                event="token_refresh_failed",
                error=str(e)
            )
            return {"success": False, "error": str(e)}
    
    async def get_current_user(self, access_token: str) -> Dict[str, Any]:
        """Get current user from access token."""
        await self._ensure_initialized()
        
        try:
            # Set the session
            self.supabase_client.client.auth.set_session(access_token, "")
            
            user_response = self.supabase_client.client.auth.get_user(access_token)
            
            if user_response.user is None:
                return {"success": False, "error": "Invalid access token"}
            
            user_id = user_response.user.id
            
            # Get user profile
            profile_result = await self.supabase_client.get_user_profile(user_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "email": user_response.user.email,
                "profile": profile_result.get("data", [{}])[0] if profile_result.get("success") else None
            }
            
        except Exception as e:
            log_therapy_event(
                event="get_user_failed",
                error=str(e)
            )
            return {"success": False, "error": str(e)}
    
    async def reset_password(self, email: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Send password reset email with enhanced validation."""
        await self._ensure_initialized()
        
        try:
            # Enhanced email validation
            from src.utils.validation import validate_email_address
            email_result = await validate_email_address(email, f"reset_{email}")
            if not email_result.is_valid:
                return {"success": False, "error": "Invalid email format"}
            
            self.supabase_client.client.auth.reset_password_email(email_result.sanitized_content)
            
            log_therapy_event(
                event="password_reset_sent",
                email=email_result.sanitized_content,
                ip_address=ip_address,
                security_score=email_result.security_score
            )
            
            return {"success": True}
            
        except Exception as e:
            log_therapy_event(
                event="password_reset_failed",
                email=email,
                error=str(e),
                ip_address=ip_address
            )
            return {"success": False, "error": str(e)}
    
    async def update_password(self, user_id: str, new_password: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Update user password with enhanced validation."""
        await self._ensure_initialized()
        
        try:
            # Enhanced password validation
            from src.utils.validation import validate_password_strength
            password_result = await validate_password_strength(new_password, f"update_{user_id}")
            if not password_result.is_valid:
                return {"success": False, "error": "Password does not meet security requirements"}
            
            auth_response = self.supabase_client.client.auth.update_user({
                "password": new_password
            })
            
            if auth_response.user is None:
                return {"success": False, "error": "Password update failed"}
            
            log_therapy_event(
                event="password_updated",
                user_id=user_id,
                ip_address=ip_address,
                security_score=password_result.security_score
            )
            
            return {"success": True}
            
        except Exception as e:
            log_therapy_event(
                event="password_update_failed",
                user_id=user_id,
                error=str(e),
                ip_address=ip_address
            )
            return {"success": False, "error": str(e)}
    
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
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
                return {"success": False, "error": str(profile_result.error)}
            
            log_therapy_event(
                event="profile_updated",
                user_id=user_id,
                updated_fields=list(updates.keys())
            )
            
            return {"success": True, "user_id": user_id, "updated_fields": list(updates.keys())}
            
        except Exception as e:
            log_therapy_event(
                event="profile_update_failed",
                user_id=user_id,
                error=str(e)
            )
            return {"success": False, "error": str(e)}
    
    async def validate_session(self, access_token: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Validate session token with security checks."""
        await self._ensure_initialized()
        
        try:
            # Get user from token
            user_response = self.supabase_client.client.auth.get_user(access_token)
            
            if user_response.user is None:
                log_therapy_event(
                    event="invalid_session_token",
                    ip_address=ip_address,
                    token_prefix=access_token[:10] if access_token else None
                )
                return {"success": False, "error": "Invalid session token"}
            
            user_id = user_response.user.id
            
            # Check if session is in our tracking
            if access_token in self.session_tokens:
                session_info = self.session_tokens[access_token]
                # Check for suspicious activity (IP change)
                if session_info.get('ip_address') != ip_address:
                    log_therapy_event(
                        event="session_ip_change_detected",
                        user_id=user_id,
                        old_ip=session_info.get('ip_address'),
                        new_ip=ip_address,
                        security_alert=True
                    )
            
            # Update session tracking
            self.session_tokens[access_token] = {
                'user_id': user_id,
                'ip_address': ip_address,
                'last_seen': datetime.utcnow()
            }
            
            return {
                "success": True,
                "user_id": user_id,
                "email": user_response.user.email
            }
            
        except Exception as e:
            log_therapy_event(
                event="session_validation_error",
                error=str(e),
                ip_address=ip_address
            )
            return {"success": False, "error": str(e)}
    
    async def revoke_session(self, access_token: str, user_id: str) -> Dict[str, Any]:
        """Revoke a specific session token."""
        try:
            # Remove from tracking
            if access_token in self.session_tokens:
                del self.session_tokens[access_token]
            
            # Sign out from Supabase
            result = await self.sign_out(user_id)
            
            log_therapy_event(
                event="session_revoked",
                user_id=user_id,
                token_prefix=access_token[:10] if access_token else None
            )
            
            return result
            
        except Exception as e:
            log_therapy_event(
                event="session_revoke_failed",
                user_id=user_id,
                error=str(e)
            )
            return {"success": False, "error": str(e)}
    
    def cleanup_expired_sessions(self):
        """Clean up expired session tracking."""
        now = datetime.utcnow()
        expired_tokens = []
        
        for token, session_info in self.session_tokens.items():
            if (now - session_info['last_seen']).seconds > 86400:  # 24 hours
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.session_tokens[token]
        
        return len(expired_tokens)


def get_auth_security_metrics() -> Dict[str, Any]:
    """Get authentication security metrics for monitoring."""
    now = datetime.utcnow()
    
    # Calculate recent login attempts
    recent_attempts = 0
    failed_recent = 0
    
    for attempts in login_attempts.values():
        for attempt in attempts:
            if (now - attempt['timestamp']).seconds < 3600:  # Last hour
                recent_attempts += 1
                if not attempt['success']:
                    failed_recent += 1
    
    return {
        'total_identifiers_tracked': len(login_attempts),
        'recent_login_attempts': recent_attempts,
        'recent_failed_attempts': failed_recent,
        'currently_blocked_ips': len(blocked_ips),
        'accounts_with_failures': len([k for k, v in failed_attempts.items() if v > 0]),
        'blocked_ip_addresses': list(blocked_ips.keys()),
        'failure_rate': failed_recent / max(recent_attempts, 1)
    }


def reset_auth_security_metrics():
    """Reset authentication security metrics (useful for testing)."""
    global login_attempts, failed_attempts, blocked_ips
    login_attempts.clear()
    failed_attempts.clear()
    blocked_ips.clear()


# High-level API wrapper functions with consistent response format
async def sign_up(request: SignUpRequest, ip_address: Optional[str] = None) -> APIResponse[Dict[str, Any]]:
    """High-level sign up with APIResponse wrapper."""
    auth_service = await get_auth_service()
    result = await auth_service.sign_up(request, ip_address)
    
    if result["success"]:
        return APIResponse(
            success=True,
            data={
                "user": {
                    "id": result["user_id"],
                    "email": result["email"]
                },
                "tokens": {
                    "access_token": result.get("access_token"),
                    "refresh_token": result.get("refresh_token"),
                    "token_type": "bearer"
                }
            },
            message="Registration successful"
        )
    else:
        return APIResponse(
            success=False,
            error=result["error"],
            error_code="SIGNUP_FAILED"
        )


async def sign_in(request: SignInRequest, ip_address: Optional[str] = None) -> APIResponse[Dict[str, Any]]:
    """High-level sign in with APIResponse wrapper."""
    auth_service = await get_auth_service()
    result = await auth_service.sign_in(request, ip_address)
    
    if result["success"]:
        return APIResponse(
            success=True,
            data={
                "user": {
                    "id": result["user_id"],
                    "email": result["email"]
                },
                "tokens": {
                    "access_token": result.get("access_token"),
                    "refresh_token": result.get("refresh_token"),
                    "token_type": "bearer"
                },
                "profile": result.get("profile")
            },
            message="Login successful"
        )
    else:
        return APIResponse(
            success=False,
            error=result["error"],
            error_code="SIGNIN_FAILED"
        )


async def sign_out(user_id: str) -> APIResponse[None]:
    """High-level sign out with APIResponse wrapper."""
    auth_service = await get_auth_service()
    result = await auth_service.sign_out(user_id)
    
    if result["success"]:
        return APIResponse(success=True, message="Logout successful")
    else:
        return APIResponse(
            success=False,
            error=result["error"],
            error_code="SIGNOUT_FAILED"
        )


async def refresh_token(refresh_token: str) -> APIResponse[Dict[str, Any]]:
    """High-level token refresh with APIResponse wrapper."""
    auth_service = await get_auth_service()
    result = await auth_service.refresh_session(refresh_token)
    
    if result["success"]:
        return APIResponse(
            success=True,
            data={
                "tokens": {
                    "access_token": result.get("access_token"),
                    "refresh_token": result.get("refresh_token"),
                    "token_type": "bearer"
                },
                "user": {
                    "id": result["user_id"],
                    "email": result["email"]
                }
            },
            message="Token refreshed successfully"
        )
    else:
        return APIResponse(
            success=False,
            error=result["error"],
            error_code="REFRESH_FAILED"
        )


async def get_current_user(access_token: str) -> APIResponse[Dict[str, Any]]:
    """High-level get current user with APIResponse wrapper."""
    auth_service = await get_auth_service()
    result = await auth_service.get_current_user(access_token)
    
    if result["success"]:
        return APIResponse(
            success=True,
            data={
                "user": {
                    "id": result["user_id"],
                    "email": result["email"]
                },
                "profile": result.get("profile")
            }
        )
    else:
        return APIResponse(
            success=False,
            error=result["error"],
            error_code="INVALID_TOKEN"
        )


async def reset_password(email: str, ip_address: Optional[str] = None) -> APIResponse[None]:
    """High-level password reset with APIResponse wrapper."""
    auth_service = await get_auth_service()
    result = await auth_service.reset_password(email, ip_address)
    
    if result["success"]:
        return APIResponse(success=True, message="Password reset email sent successfully")
    else:
        return APIResponse(
            success=False,
            error=result["error"],
            error_code="RESET_FAILED"
        )


async def oauth_sign_in(request: OAuthRequest) -> APIResponse[Dict[str, Any]]:
    """High-level OAuth sign in with APIResponse wrapper."""
    auth_service = await get_auth_service()
    result = await auth_service.oauth_sign_in(request)
    
    if result["success"]:
        return APIResponse(
            success=True,
            data={
                "auth_url": result.get("auth_url"),
                "provider": result.get("provider")
            },
            message="OAuth authentication initiated"
        )
    else:
        return APIResponse(
            success=False,
            error=result["error"],
            error_code="OAUTH_FAILED"
        )


# Global auth service instance
_auth_service: Optional[AuthService] = None


async def get_auth_service() -> AuthService:
    """Get initialized enhanced auth service."""
    global _auth_service
    
    if _auth_service is None:
        _auth_service = AuthService()
        await _auth_service._ensure_initialized()
    
    return _auth_service


