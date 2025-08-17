# Application constants
from enum import Enum

class ResponseMessages:
    """Centralized response messages to avoid duplication"""
    CRISIS_SUPPORT = (
        "I'm here for you. It sounds like you're going through something very difficult. "
        "Please know you're not alone. If you're in immediate danger or need urgent help, "
        "contact a mental health professional or crisis helpline in your area."
    )
    
    UNSAFE_CONTENT_BLOCKED = "Your input contains unsafe content and has been blocked."
    PROMPT_INJECTION_BLOCKED = "Your input appears to contain prompt injection and has been blocked."
    PII_DETECTED = "Your message contains sensitive personal information. Please remove or rephrase it."
    UNSAFE_RESPONSE_BLOCKED = "Response blocked due to safety concerns."
    PII_INPUT_BLOCKED = "Input blocked due to PII."
    
    MISSING_ACCESS_TOKEN = "Missing access token"
    INVALID_TOKEN = "Invalid token"
    INVALID_MESSAGE = "Invalid message"
    RATE_LIMIT_EXCEEDED = "Rate limit exceeded"
    THERAPY_FLOW_FAILED = "Failed to run therapy flow"
    INTERNAL_SERVER_ERROR = "Internal server error"

class SystemPrompts:
    """Centralized system prompts"""
    THERAPIST_BASE = "You are a compassionate therapist."
    PROVIDE_SUPPORT = "Provide supportive, professional, non-diagnostic responses."
    
    JOURNAL_CLASSIFIER = (
        "You classify if a user message is a journal entry or a request for therapy chat. "
        "Reply ONLY with 'journal' or 'chat'."
    )

class Limits:
    """Application limits and thresholds"""
    RATE_LIMIT_PER_MIN = 60
    MEMORY_HISTORY_LIMIT = 6
    RELEVANT_MEMORIES_LIMIT = 5
    SUMMARY_MAX_LENGTH = 800
    MEMORY_CONTENT_MAX_LENGTH = 300
    
    # WebSocket close codes
    WS_MISSING_TOKEN = 4000
    WS_INVALID_TOKEN = 4001
    WS_INTERNAL_ERROR = 5000

class NodeNames:
    """Graph node names for consistency"""
    CHECK_INPUT_MODERATION = "check_input_moderation"
    HANDLE_BLOCKED = "handle_blocked"
    HANDLE_INJECTION = "handle_injection"
    CHECK_PII = "check_pii"
    HANDLE_PII = "handle_pii"
    ANALYZE_EMOTION = "analyze_emotion"
    CHECK_CRISIS = "check_crisis"
    CRISIS = "crisis"
    CHECK_JOURNAL = "check_journal"
    JOURNAL = "journal"
    CHAT = "chat"
    HANDLE_UNSAFE_RESPONSE = "handle_unsafe_response"

class ClassificationResults:
    """Classification result constants"""
    JOURNAL = "journal"
    CHAT = "chat"
    SAFE = "safe"
    UNSAFE = "unsafe"
    CRISIS = "crisis"
