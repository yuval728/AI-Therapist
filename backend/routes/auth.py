from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from services.auth_services import SupabaseAuthService, get_current_user

router = APIRouter()

class SignInRequest(BaseModel):
    email: str
    password: str

class SignUpRequest(BaseModel):
    email: str
    password: str

class OAuthRequest(BaseModel):
    provider: str  # "google", "github", etc.

class User(BaseModel):
    id: str
    email: str

@router.post("/signup", response_model=User)
async def sign_up(data: SignUpRequest):
    user = await SupabaseAuthService.sign_up(data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signup failed")
    return user

@router.post("/signin", response_model=User)
async def sign_in(data: SignInRequest):
    user = await SupabaseAuthService.sign_in(data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user

@router.post("/oauth", response_model=User)
async def oauth_login(data: OAuthRequest):
    # This will just return a redirect URL to the provider's login page
    url = SupabaseAuthService.get_oauth_url(data.provider)
    return {"url": url}

@router.get("/me", response_model=User)
async def me(user=Depends(get_current_user)):
    return user
