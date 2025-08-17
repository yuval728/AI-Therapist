"""Database integration module for AI therapist."""

from .supabase_client import (
    SupabaseClient,
    DatabaseConfig,
    QueryResult,
    get_supabase_client,
    supabase_session
)

__all__ = [
    "SupabaseClient",
    "DatabaseConfig", 
    "QueryResult",
    "get_supabase_client",
    "supabase_session"
]
