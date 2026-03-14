"""Enhanced input moderation with comprehensive safety checks."""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from src.models.enums import AttackType
from src.utils import log_security_event


@dataclass
class ModerationResult:
    """Structured moderation result with detailed information."""
    is_safe: bool
    attack_type: AttackType
    confidence: float
    matched_patterns: List[str]
    severity: str = "MEDIUM"
    
    def to_dict(self) -> Dict:
        return {
            "is_safe": self.is_safe,
            "attack_type": self.attack_type.value,
            "confidence": self.confidence,
            "matched_patterns": self.matched_patterns,
            "severity": self.severity
        }


class ContentModerator:
    """Enhanced content moderation with configurable patterns and thresholds."""
    
    def __init__(self):
        self.unsafe_patterns = self._load_unsafe_patterns()
        self.injection_patterns = self._load_injection_patterns()
        self.dangerous_response_patterns = self._load_dangerous_response_patterns()
    
    def _load_unsafe_patterns(self) -> List[Tuple[str, str, float]]:
        """Load unsafe content patterns with severity and confidence."""
        return [
            # Self-harm patterns (HIGH severity)
            (r"\b(kill|hurt|harm)\s+(myself|me)\b", "HIGH", 0.9),
            (r"\bsuicide\b", "HIGH", 0.8),
            (r"\bcut\s+(myself|me)\b", "HIGH", 0.9),
            (r"\bend\s+my\s+life\b", "HIGH", 0.9),
            (r"\bself[\s-]harm\b", "HIGH", 0.8),
            
            # Violence patterns (HIGH severity)
            (r"\b(murder|kill|shoot|stab)\s+someone\b", "HIGH", 0.9),
            (r"\bschool\s+shooting\b", "CRITICAL", 1.0),
            (r"\bbomb\b", "HIGH", 0.7),
            (r"\bterrorism\b", "HIGH", 0.8),
            
            # Abuse patterns (MEDIUM severity)
            (r"\b(rape|sexual\s+assault)\b", "HIGH", 0.8),
            (r"\babuse\b", "MEDIUM", 0.6),
            (r"\bhate\s+speech\b", "MEDIUM", 0.7),
            
            # General violence (MEDIUM severity)
            (r"\bviolence\b", "MEDIUM", 0.5),
            (r"\bhurt\s+others\b", "MEDIUM", 0.7),
        ]
    
    def _load_injection_patterns(self) -> List[Tuple[str, float]]:
        """Load prompt injection patterns with confidence scores."""
        return [
            (r"ignore\s+(the\s+)?previous\s+instructions?", 0.9),
            (r"disregard\s+(the\s+)?above", 0.8),
            (r"act\s+as\s+(?!a\s+therapist)", 0.7),
            (r"simulate\s+(?!therapy)", 0.7),
            (r"pretend\s+to\s+be\s+(?!supportive)", 0.7),
            (r"bypass\s+(?:safety|security|guidelines)", 0.9),
            (r"jailbreak", 0.8),
            (r"you\s+are\s+now\s+(?!a\s+therapist)", 0.7),
            (r"system\s*:\s*", 0.6),
            (r"assistant\s*:\s*", 0.6),
            (r"<\|.*?\|>", 0.8),
            (r"```.*?system.*?```", 0.9),
        ]
    
    def _load_dangerous_response_patterns(self) -> List[Tuple[str, str, float]]:
        """Load dangerous AI response patterns."""
        return [
            # Harmful advice (CRITICAL)
            (r"you\s+should\s+just\s+give\s+up", "CRITICAL", 1.0),
            (r"go\s+ahead\s+and\s+hurt\s+yourself", "CRITICAL", 1.0),
            (r"no\s+one\s+cares\s+about\s+you", "CRITICAL", 1.0),
            (r"you\s+are\s+worthless", "CRITICAL", 1.0),
            
            # Medical advice (HIGH)
            (r"I\s+diagnose\s+you", "HIGH", 0.9),
            (r"take\s+(?:this\s+)?medication", "HIGH", 0.8),
            (r"you\s+have\s+(?:depression|anxiety|bipolar)", "HIGH", 0.8),
            
            # Inappropriate instructions (HIGH)
            (r"here's\s+how\s+to\s+(?:hurt|harm|kill)", "CRITICAL", 1.0),
            (r"follow\s+these\s+steps\s+to", "MEDIUM", 0.6),
        ]
    
    def moderate_input(self, text: str, user_id: Optional[str] = None) -> ModerationResult:
        """Comprehensive input moderation with detailed results."""
        if not text or not text.strip():
            return ModerationResult(
                is_safe=True,
                attack_type=AttackType.SAFE,
                confidence=1.0,
                matched_patterns=[]
            )
        
        # Check for unsafe content
        unsafe_result = self._check_unsafe_content(text)
        if not unsafe_result.is_safe:
            self._log_moderation_event("unsafe_content_detected", unsafe_result, user_id)
            return unsafe_result
        
        # Check for prompt injection
        injection_result = self._check_prompt_injection(text)
        if not injection_result.is_safe:
            self._log_moderation_event("prompt_injection_detected", injection_result, user_id)
            return injection_result
        
        return ModerationResult(
            is_safe=True,
            attack_type=AttackType.SAFE,
            confidence=1.0,
            matched_patterns=[]
        )
    
    def moderate_output(self, text: str, user_id: Optional[str] = None) -> ModerationResult:
        """Moderate AI-generated output for safety."""
        if not text or not text.strip():
            return ModerationResult(
                is_safe=True,
                attack_type=AttackType.SAFE,
                confidence=1.0,
                matched_patterns=[]
            )
        
        matched_patterns = []
        max_confidence = 0.0
        max_severity = "LOW"
        
        for pattern, severity, confidence in self.dangerous_response_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matched_patterns.append(pattern)
                max_confidence = max(max_confidence, confidence)
                if severity in ["CRITICAL", "HIGH"] and max_severity in ["LOW", "MEDIUM"]:
                    max_severity = severity
        
        is_safe = len(matched_patterns) == 0
        attack_type = AttackType.UNSAFE_OUTPUT if not is_safe else AttackType.SAFE
        
        result = ModerationResult(
            is_safe=is_safe,
            attack_type=attack_type,
            confidence=max_confidence,
            matched_patterns=matched_patterns,
            severity=max_severity
        )
        
        if not is_safe:
            self._log_moderation_event("unsafe_output_detected", result, user_id)
        
        return result
    
    def _check_unsafe_content(self, text: str) -> ModerationResult:
        """Check for unsafe content patterns."""
        matched_patterns = []
        max_confidence = 0.0
        max_severity = "LOW"
        
        for pattern, severity, confidence in self.unsafe_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matched_patterns.append(pattern)
                max_confidence = max(max_confidence, confidence)
                if severity in ["CRITICAL", "HIGH"] and max_severity in ["LOW", "MEDIUM"]:
                    max_severity = severity
        
        is_safe = len(matched_patterns) == 0
        attack_type = AttackType.BLOCKED if not is_safe else AttackType.SAFE
        
        return ModerationResult(
            is_safe=is_safe,
            attack_type=attack_type,
            confidence=max_confidence,
            matched_patterns=matched_patterns,
            severity=max_severity
        )
    
    def _check_prompt_injection(self, text: str) -> ModerationResult:
        """Check for prompt injection attempts."""
        matched_patterns = []
        max_confidence = 0.0
        
        for pattern, confidence in self.injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matched_patterns.append(pattern)
                max_confidence = max(max_confidence, confidence)
        
        is_safe = len(matched_patterns) == 0
        attack_type = AttackType.INJECTED if not is_safe else AttackType.SAFE
        
        return ModerationResult(
            is_safe=is_safe,
            attack_type=attack_type,
            confidence=max_confidence,
            matched_patterns=matched_patterns,
            severity="HIGH" if max_confidence > 0.8 else "MEDIUM"
        )
    
    def _log_moderation_event(
        self,
        event: str,
        result: ModerationResult,
        user_id: Optional[str]
    ) -> None:
        """Log moderation events for monitoring."""
        log_security_event(
            event=event,
            attack_type=result.attack_type.value,
            user_id=user_id,
            severity=result.severity,
            confidence=result.confidence,
            matched_patterns=result.matched_patterns
        )


# Global moderator instance
_moderator = ContentModerator()


# Backward compatibility functions
def contains_unsafe_content(text: str) -> bool:
    """Legacy function for backward compatibility."""
    result = _moderator.moderate_input(text)
    return not result.is_safe


def detect_prompt_injection(text: str) -> bool:
    """Legacy function for backward compatibility."""
    result = _moderator.moderate_input(text)
    return result.attack_type == AttackType.INJECTED


def contains_dangerous_response(text: str) -> bool:
    """Legacy function for backward compatibility."""
    result = _moderator.moderate_output(text)
    return not result.is_safe


# New enhanced functions
def moderate_input(text: str, user_id: Optional[str] = None) -> ModerationResult:
    """Enhanced input moderation with detailed results."""
    return _moderator.moderate_input(text, user_id)


def moderate_output(text: str, user_id: Optional[str] = None) -> ModerationResult:
    """Enhanced output moderation with detailed results."""
    return _moderator.moderate_output(text, user_id)
