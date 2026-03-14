"""Models package for the AI therapist application."""
from .base import (
    TimestampMixin,
    BaseEntity,
    APIResponse,
    PaginationParams,
    PaginatedResponse
)
from .enums import (
    AttackType,
    SessionMode,
    EmotionType,
    CrisisLevel,
    MessageType,
    ProcessingStatus,
    UserRole
)
from .auth_models import (
    SignInRequest,
    SignUpRequest,
    OAuthRequest,
    TokenResponse,
    User,
    UserSession,
    PasswordResetRequest,
    PasswordResetConfirm,
    UserPreferences
)
from .state import (
    TherapyState,
    TherapySession,
    SessionMessage,
    MemoryEntry,
    CrisisEvent,
    JournalEntry,
    ClassificationFormat
)

__all__ = [
    # Base models
    "TimestampMixin",
    "BaseEntity", 
    "APIResponse",
    "PaginationParams",
    "PaginatedResponse",
    
    # Enums
    "AttackType",
    "SessionMode",
    "EmotionType", 
    "CrisisLevel",
    "MessageType",
    "ProcessingStatus",
    "UserRole",
    
    # Auth models
    "SignInRequest",
    "SignUpRequest",
    "OAuthRequest",
    "TokenResponse",
    "User",
    "UserSession", 
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "UserPreferences",
    
    # State models
    "TherapyState",
    "TherapySession",
    "SessionMessage",
    "MemoryEntry",
    "CrisisEvent",
    "JournalEntry",
    "ClassificationFormat"
]
