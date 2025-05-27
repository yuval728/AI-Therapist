# app/services/auth_service.py
import os
from supabase import create_client, Client
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
import urllib.parse

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

class User(BaseModel):
    id: str
    email: str

class SupabaseAuthService:
    @staticmethod
    async def sign_up(email: str, password: str) -> User | None:
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.user:
            return User(id=response.user.id, email=response.user.email)
        return None

    @staticmethod
    async def sign_in(email: str, password: str) -> User | None:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            return User(id=response.user.id, email=response.user.email)
        return None

    @staticmethod
    def get_oauth_url(provider: str) -> str:
        # Construct redirect URL for OAuth sign-in (adjust redirect URL to your frontend)
        redirect_uri = urllib.parse.quote("https://yourfrontend.com/oauth/callback")
        return f"{SUPABASE_URL}/auth/v1/authorize?provider={provider}&redirect_to={redirect_uri}"

    @staticmethod
    def verify_jwt(token: str) -> User:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return User(id=payload["sub"], email=payload["email"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token = credentials.credentials
    return SupabaseAuthService.verify_jwt(token)

