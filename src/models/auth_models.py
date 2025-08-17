"""Authentication and user management models."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from .base import BaseEntity
from .enums import UserRole


class SignInRequest(BaseModel):
    """User sign-in request model."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    remember_me: bool = Field(default=False, description="Extended session duration")


class SignUpRequest(BaseModel):
    """User registration request model."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    confirm_password: str = Field(..., description="Password confirmation")
    first_name: Optional[str] = Field(None, max_length=50, description="User first name")
    last_name: Optional[str] = Field(None, max_length=50, description="User last name")
    terms_accepted: bool = Field(..., description="Terms of service acceptance")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('terms_accepted')
    def terms_must_be_accepted(cls, v):
        if not v:
            raise ValueError('Terms of service must be accepted')
        return v


class OAuthRequest(BaseModel):
    """OAuth authentication request model."""
    provider: str = Field(..., regex=r'^(google|github|apple|facebook)$')
    redirect_url: Optional[str] = Field(None, description="Custom redirect URL")


class TokenResponse(BaseModel):
    """Authentication token response model."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    expires_at: datetime = Field(..., description="Token expiration timestamp")


class User(BaseEntity):
    """User profile model."""
    email: EmailStr = Field(..., description="User email address")
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    role: UserRole = Field(default=UserRole.CLIENT)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    last_login: Optional[datetime] = None
    login_count: int = Field(default=0, ge=0)
    preferences: dict = Field(default_factory=dict)
    
    @property
    def full_name(self) -> Optional[str]:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name


class UserSession(BaseEntity):
    """User session tracking model."""
    user_id: str = Field(..., description="User identifier")
    session_token: str = Field(..., description="Session token hash")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    is_active: bool = Field(default=True)
    expires_at: datetime = Field(..., description="Session expiration")
    last_activity: datetime = Field(default_factory=datetime.utcnow)


class PasswordResetRequest(BaseModel):
    """Password reset request model."""
    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model."""
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., description="Password confirmation")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class UserPreferences(BaseModel):
    """User preferences and settings."""
    theme: str = Field(default="light", regex=r'^(light|dark|auto)$')
    language: str = Field(default="en", regex=r'^[a-z]{2}$')
    timezone: str = Field(default="UTC")
    notifications_enabled: bool = Field(default=True)
    crisis_alerts_enabled: bool = Field(default=True)
    data_retention_days: int = Field(default=365, ge=30, le=3650)
