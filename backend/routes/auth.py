from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from models.models import SignInRequest, SignUpRequest, OAuthRequest, User
from services.auth_services import SupabaseAuthService, get_current_user

router = APIRouter()


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
