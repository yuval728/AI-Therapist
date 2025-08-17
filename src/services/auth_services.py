from supabase import create_client, Client
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.models.auth_models import User
from src.utils.error_handling import handle_auth_error, AuthenticationError
import jwt
import urllib.parse
from src.config.config import get_settings
from loguru import logger

_settings = get_settings()
supabase: Client = create_client(_settings.supabase_url, _settings.supabase_key)
security = HTTPBearer()
JWT_SECRET = _settings.supabase_key  # Supabase uses service key for JWT verify if using anon key pattern
JWT_ALGORITHM = _settings.jwt_algorithm

class SupabaseAuthService:
    @staticmethod
    async def sign_up(email: str, password: str) -> User | None:
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.user:
            # Supabase may not always immediately give session on sign_up (email confirmation). Return minimal user.
            return User(id=response.user.id, email=response.user.email)
        return None

    @staticmethod
    async def sign_in(email: str, password: str) -> User | None:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user and response.session:
            return User(
                id=response.user.id,
                email=response.user.email,
                access_token=response.session.access_token,
                refresh_token=getattr(response.session, "refresh_token", None),
                expires_in=getattr(response.session, "expires_in", None),
            )
        return None

    @staticmethod
    def get_oauth_url(provider: str) -> str:
        """Return Supabase OAuth authorization URL for the given provider."""
        redirect_uri = urllib.parse.quote(_settings.supabase_redirect_url, safe="")
        return (
            f"{_settings.supabase_url}/auth/v1/authorize?provider={provider}&redirect_to={redirect_uri}"
        )

    @staticmethod
    def verify_jwt(token: str) -> User:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM],  options={"verify_aud": False, "verify_iat": True})
            # Optionally fetch user to ensure not revoked
            try:
                supabase.auth.get_user(token)
            except Exception as e:  # noqa
                logger.warning(f"Supabase get_user failed: {e}")
            return User(id=payload.get("sub", "unknown"), email=payload.get("email", "unknown@example.com"))
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
