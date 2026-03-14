"""Enhanced PII detection with comprehensive patterns and confidence scoring."""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from src.models.enums import AttackType
from src.utils import log_security_event


@dataclass
class PIIDetectionResult:
    """Structured PII detection result."""
    has_pii: bool
    pii_types: List[str]
    confidence: float
    matched_patterns: List[str]
    redacted_text: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "has_pii": self.has_pii,
            "pii_types": self.pii_types,
            "confidence": self.confidence,
            "matched_patterns": self.matched_patterns,
            "redacted_text": self.redacted_text
        }


class PIIDetector:
    """Enhanced PII detection with multiple pattern types and confidence scoring."""
    
    def __init__(self):
        self.pii_patterns = self._load_pii_patterns()
    
    def _load_pii_patterns(self) -> List[Tuple[str, str, str, float]]:
        """Load PII patterns with type, replacement, and confidence."""
        return [
            # Social Security Numbers
            (r"\b\d{3}-\d{2}-\d{4}\b", "SSN", "[SSN-REDACTED]", 0.95),
            (r"\b\d{9}\b", "SSN", "[SSN-REDACTED]", 0.7),
            
            # Phone Numbers
            (r"\b(?:\+1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b", "PHONE", "[PHONE-REDACTED]", 0.9),
            (r"\b\d{10}\b", "PHONE", "[PHONE-REDACTED]", 0.6),
            
            # Email Addresses
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL", "[EMAIL-REDACTED]", 0.95),
            
            # Credit Card Numbers
            (r"\b(?:\d[ -]*?){13,16}\b", "CREDIT_CARD", "[CARD-REDACTED]", 0.8),
            (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b", "CREDIT_CARD", "[CARD-REDACTED]", 0.95),
            
            # ZIP Codes
            (r"\b\d{5}(-\d{4})?\b", "ZIP_CODE", "[ZIP-REDACTED]", 0.7),
            
            # Driver's License (common patterns)
            (r"\b[A-Z]{1,2}\d{6,8}\b", "DRIVERS_LICENSE", "[DL-REDACTED]", 0.6),
            
            # Bank Account Numbers
            (r"\b\d{8,17}\b", "BANK_ACCOUNT", "[ACCOUNT-REDACTED]", 0.5),
            
            # IP Addresses
            (r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", "IP_ADDRESS", "[IP-REDACTED]", 0.8),
            
            # Medical Record Numbers
            (r"\bMRN[\s:]?\d{6,10}\b", "MEDICAL_RECORD", "[MRN-REDACTED]", 0.9),
            
            # Passport Numbers
            (r"\b[A-Z]{1,2}\d{6,9}\b", "PASSPORT", "[PASSPORT-REDACTED]", 0.6),
            
            # Date of Birth patterns
            (r"\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b", "DOB", "[DOB-REDACTED]", 0.8),
            (r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+(?:19|20)\d{2}\b", "DOB", "[DOB-REDACTED]", 0.7),
        ]
    
    def detect_pii(self, text: str, user_id: Optional[str] = None) -> PIIDetectionResult:
        """Comprehensive PII detection with confidence scoring."""
        if not text or not text.strip():
            return PIIDetectionResult(
                has_pii=False,
                pii_types=[],
                confidence=0.0,
                matched_patterns=[]
            )
        
        detected_types = set()
        matched_patterns = []
        confidences = []
        redacted_text = text
        
        for pattern, pii_type, replacement, confidence in self.pii_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                detected_types.add(pii_type)
                matched_patterns.append(pattern)
                confidences.append(confidence)
                
                # Redact the matched text
                for match in reversed(matches):  # Reverse to maintain indices
                    redacted_text = (
                        redacted_text[:match.start()] + 
                        replacement + 
                        redacted_text[match.end():]
                    )
        
        has_pii = len(detected_types) > 0
        max_confidence = max(confidences) if confidences else 0.0
        
        result = PIIDetectionResult(
            has_pii=has_pii,
            pii_types=list(detected_types),
            confidence=max_confidence,
            matched_patterns=matched_patterns,
            redacted_text=redacted_text if has_pii else None
        )
        
        if has_pii:
            self._log_pii_detection(result, user_id)
        
        return result
    
    def _log_pii_detection(self, result: PIIDetectionResult, user_id: Optional[str]) -> None:
        """Log PII detection events."""
        log_security_event(
            event="pii_detected",
            attack_type=AttackType.PII_FOUND.value,
            user_id=user_id,
            severity="HIGH" if result.confidence > 0.8 else "MEDIUM",
            pii_types=result.pii_types,
            confidence=result.confidence
        )
    
    def redact_pii(self, text: str) -> str:
        """Redact PII from text and return cleaned version."""
        result = self.detect_pii(text)
        return result.redacted_text if result.redacted_text else text


# Global detector instance
_pii_detector = PIIDetector()


# Backward compatibility function
def detect_pii(text: str) -> bool:
    """Legacy function for backward compatibility."""
    result = _pii_detector.detect_pii(text)
    return result.has_pii


# New enhanced functions
def detect_pii_enhanced(text: str, user_id: Optional[str] = None) -> PIIDetectionResult:
    """Enhanced PII detection with detailed results."""
    return _pii_detector.detect_pii(text, user_id)


def redact_pii(text: str) -> str:
    """Redact PII from text."""
    return _pii_detector.redact_pii(text)