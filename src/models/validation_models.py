"""Validation-related models for the AI therapist application."""
from typing import List, Optional
from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Structured validation result with security metadata."""
    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    sanitized_content: Optional[str] = None
    security_score: int = 100  # 0-100, lower is more suspicious
    detected_threats: List[str] = Field(default_factory=list)
    entropy_score: float = 0.0
    processing_time: float = 0.0


class SecurityConfig(BaseModel):
    """Configuration for security validation."""
    max_length: int = 5000
    min_length: int = 1
    allow_html: bool = False
    strict_mode: bool = True
    check_entropy: bool = True
    rate_limit_enabled: bool = True