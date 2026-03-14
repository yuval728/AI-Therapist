"""Authentication module for AI therapist."""

from .supabase_auth import (
    SupabaseAuth,
    AuthResult,
    get_auth_service
)

__all__ = [
    "SupabaseAuth",
    "AuthResult", 
    "get_auth_service"
]
