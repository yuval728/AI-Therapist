"""State models for therapy session management."""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from langchain_core.messages import BaseMessage
from .base import BaseEntity, TimestampMixin
from .enums import AttackType, SessionMode, EmotionType, CrisisLevel, ProcessingStatus


class TherapyState(BaseModel):
    """Core state for therapy graph execution."""
    user_id: str
    session_id: str
    input: str
    messages: List[BaseMessage]
    response: Optional[str]
    relevant_memories: Optional[List[str]]
    emotion: Optional[str]
    emotion_confidence: Optional[float]
    is_crisis: Optional[bool]
    crisis_level: Optional[str]
    mode: Optional[str]
    journal_entry: Optional[str]
    attack: Optional[str]
    summary: Optional[str]
    metadata: Optional[Dict[str, Any]]


class TherapySession(BaseEntity):
    """Comprehensive therapy session model."""
    user_id: str = Field(..., description="User identifier")
    mode: SessionMode = Field(default=SessionMode.CHAT)
    emotion_detected: Optional[EmotionType] = None
    emotion_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    crisis_detected: bool = False
    crisis_level: Optional[CrisisLevel] = None
    message_count: int = Field(default=0, ge=0)
    duration_seconds: Optional[int] = Field(None, ge=0)
    summary: Optional[str] = Field(None, max_length=1000)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    is_active: bool = True
    ended_at: Optional[datetime] = None
    
    @field_validator('emotion_confidence')
    def validate_emotion_confidence(cls, v, values):
        if v is not None and 'emotion_detected' not in values:
            raise ValueError('emotion_confidence requires emotion_detected')
        return v


class SessionMessage(BaseEntity):
    """Individual message within a therapy session."""
    session_id: str = Field(..., description="Parent session ID")
    user_id: str = Field(..., description="User identifier")
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: str = Field(..., pattern=r'^(user|assistant|system)$')
    emotion_detected: Optional[EmotionType] = None
    emotion_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    attack_detected: Optional[AttackType] = None
    is_flagged: bool = False
    processing_time_ms: Optional[int] = Field(None, ge=0)
    

class MemoryEntry(BaseEntity):
    """Long-term memory storage for therapy context."""
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Source session ID")
    content: str = Field(..., min_length=1, max_length=2000)
    embedding_vector: Optional[List[float]] = None
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    emotion_context: Optional[EmotionType] = None
    tags: List[str] = Field(default_factory=list)
    is_archived: bool = False
    

class CrisisEvent(BaseEntity):
    """Crisis detection and escalation tracking."""
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Source session ID")
    message_id: Optional[str] = None
    crisis_level: CrisisLevel = Field(..., description="Severity level")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    trigger_content: str = Field(..., description="Content that triggered detection")
    escalated: bool = False
    escalation_method: Optional[str] = None
    resolved: bool = False
    resolution_notes: Optional[str] = None
    

class JournalEntry(BaseEntity):
    """User journal entries for reflection."""
    user_id: str = Field(..., description="User identifier")
    session_id: Optional[str] = None
    title: Optional[str] = Field(None, max_length=200)
    content: str = Field(..., min_length=1, max_length=10000)
    mood_rating: Optional[int] = Field(None, ge=1, le=10)
    emotion_tags: List[EmotionType] = Field(default_factory=list)
    is_private: bool = True
    word_count: int = Field(default=0, ge=0)
    
    @field_validator('word_count', mode="before")
    def calculate_word_count(cls, v, values):
        if 'content' in values:
            return len(values['content'].split())
        return v