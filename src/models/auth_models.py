from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str

class OAuthRequest(BaseModel):
    provider: str  # "google", "github", etc.

class User(BaseModel):
    id: str
    email: EmailStr
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
