"""Chat-related models for the AI therapist application."""
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class ChatMessageRequest(BaseModel):
    """Request model for sending chat messages."""
    content: str = Field(..., min_length=1, max_length=4000, description="Message content")
    session_id: Optional[str] = Field(None, description="Session ID (auto-created if not provided)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('content')
    def validate_content(cls, v):
        """Validate and sanitize message content."""
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        # Basic sanitization
        return v.strip()
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata size to prevent bloat."""
        if v and len(str(v)) > 1000:  # Limit metadata size
            raise ValueError("Metadata too large")
        return v or {}


class ChatMessageResponse(BaseModel):
    """Response model for chat messages."""
    message_id: str = Field(..., description="Unique message identifier")
    session_id: str = Field(..., description="Session identifier")
    content: str = Field(..., description="AI response content")
    emotion: Optional[str] = Field(None, description="Detected emotion")
    crisis_level: Optional[str] = Field(None, description="Detected crisis level")
    mode: Optional[str] = Field(None, description="Therapy mode used")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional response metadata")
    timestamp: datetime = Field(..., description="Response timestamp")


class TypingStatusResponse(BaseModel):
    """Response model for typing status."""
    session_id: str = Field(..., description="Session identifier")
    is_typing: bool = Field(..., description="Whether AI is currently typing")
    estimated_time_ms: Optional[int] = Field(None, description="Estimated response time")
    timestamp: datetime = Field(..., description="Status timestamp")


class StreamingChatResponse(BaseModel):
    """Response model for streaming chat."""
    message_id: str = Field(..., description="Unique message identifier")
    session_id: str = Field(..., description="Session identifier")
    chunk: str = Field(..., description="Response chunk")
    is_final: bool = Field(..., description="Whether this is the final chunk")
    emotion: Optional[str] = Field(None, description="Detected emotion (in final chunk)")
    crisis_level: Optional[str] = Field(None, description="Detected crisis level (in final chunk)")
    mode: Optional[str] = Field(None, description="Therapy mode (in final chunk)")
    timestamp: datetime = Field(..., description="Chunk timestamp")