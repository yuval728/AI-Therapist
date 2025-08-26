"""Enumeration types for the AI therapist application."""
from enum import Enum


class AttackType(str, Enum):
    """Types of security attacks or safety issues."""
    SAFE = "safe"
    BLOCKED = "blocked"
    INJECTED = "prompt_injection"
    PII_FOUND = "pii_found"
    UNSAFE_OUTPUT = "unsafe_output"
    MALICIOUS_CONTENT = "malicious_content"
    SPAM = "spam"


class SessionMode(str, Enum):
    """Therapy session interaction modes."""
    CHAT = "chat"
    JOURNAL = "journal"
    CRISIS = "crisis"
    REFLECTION = "reflection"


class EmotionType(str, Enum):
    """Detected emotional states."""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    NEUTRAL = "neutral"
    CONFUSED = "confused"
    EXCITED = "excited"
    CALM = "calm"
    FRUSTRATED = "frustrated"
    HOPEFUL = "hopeful"
    LONELY = "lonely"
    OVERWHELMED = "overwhelmed"


class CrisisLevel(str, Enum):
    """Crisis severity levels."""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class MessageType(str, Enum):
    """Types of messages in therapy sessions."""
    USER = "user_input"
    ASSISTANT = "ai_response"
    SYSTEM = "system_message"
    JOURNAL = "journal_entry"


class ProcessingStatus(str, Enum):
    """Status of message or session processing."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class UserRole(str, Enum):
    """User roles in the system."""
    CLIENT = "client"
    THERAPIST = "therapist"
    ADMIN = "admin"
    MODERATOR = "moderator"
