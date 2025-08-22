"""Database integration module for AI therapist."""

from .supabase_client import (
    SupabaseClient,
    QueryResult,
    get_supabase_client,
    supabase_session
)

__all__ = [
    "SupabaseClient",
    "QueryResult",
    "get_supabase_client",
    "supabase_session"
]
