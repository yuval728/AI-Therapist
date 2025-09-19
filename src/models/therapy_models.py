"""Therapy tool models for the AI therapist application."""
from pydantic import BaseModel
from src.models.enums import EmotionType, CrisisLevel


class CrisisAnalyzer(BaseModel):
    """Model for crisis analysis results."""
    crisis: CrisisLevel


class EmotionAnalyzer(BaseModel):
    """Model for emotion analysis results."""
    emotion: EmotionType