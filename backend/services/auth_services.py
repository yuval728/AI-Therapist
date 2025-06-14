from supabase import create_client, Client
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.models.models import User
import jwt
import os
import urllib.parse
import dotenv

dotenv.load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL environment variable not set")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY environment variable not set")
SUPABASE_REDIRECT_URL = os.getenv("SUPABASE_REDIRECT_URL", "http://localhost:5173/oauth/callback")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable not set")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

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
            return User(
                id=response.user.id,
                email=response.user.email,
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                expires_in=response.session.expires_in,
            )
        return None

    @staticmethod
    def get_oauth_url(provider: str) -> str:

        redirect_uri = urllib.parse.quote(SUPABASE_REDIRECT_URL, safe="")
        return f"{SUPABASE_URL}/auth/v1/authorize?provider={provider}&redirect_to={redirect_uri}"

    @staticmethod
    def verify_jwt(token: str) -> User:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM],  options={"verify_aud": False, "verify_iat": True})
            return User(id=payload["sub"], email=payload["email"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError as e:
            print(f"Invalid token error: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        except jwt.DecodeError as e:
            print(f"Token decode error: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token decode error")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token = credentials.credentials
    return SupabaseAuthService.verify_jwt(token)
