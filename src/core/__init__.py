"""Core module for AI therapist application."""
from .llm_utils import (
    LLMClient,
    CompletionRequest,
    async_completion,
    chat_completion,
    classify_text,
    get_llm_stats
)
from .guardrails.input_moderation import (
    ContentModerator,
    ModerationResult,
    contains_unsafe_content,
    detect_prompt_injection,
    contains_dangerous_response,
    moderate_input,
    moderate_output
)
from .guardrails.pii_detection import (
    PIIDetector,
    PIIDetectionResult,
    detect_pii,
    detect_pii_enhanced,
    redact_pii
)

__all__ = [
    # LLM utilities
    "LLMClient",
    "CompletionRequest",
    "async_completion",
    "chat_completion",
    "classify_text",
    "get_llm_stats",
    
    # Input moderation
    "ContentModerator",
    "ModerationResult",
    "contains_unsafe_content",
    "detect_prompt_injection", 
    "contains_dangerous_response",
    "moderate_input",
    "moderate_output",
    
    # PII detection
    "PIIDetector",
    "PIIDetectionResult",
    "detect_pii",
    "detect_pii_enhanced",
    "redact_pii"
]
