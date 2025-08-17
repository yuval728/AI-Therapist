from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

class Settings(BaseSettings):
    # Core
    app_name: str = "AI Therapist API"
    environment: str = "dev"
    debug: bool = True

    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_redirect_url: str = "http://localhost:5173/oauth/callback"

    # Auth / JWT
    jwt_algorithm: str = "HS256"
    # Optionally allow verifying via supabase introspection

    # Models
    model_chat: str = "gemini/gemini-2.0-flash"
    model_light: str = "gemini/gemini-2.0-flash-lite"
    temperature_chat: float = 0.2
    temperature_classifiers: float = 0.0

    # Rate limiting
    rate_limit_ws_per_min: int = 60

    # Safety / feature flags
    enable_crisis_escalation: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore
