import re
import hashlib
import html
import asyncio
from typing import Any, Dict, List, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from email_validator import validate_email, EmailNotValidError
import bleach
from loguru import logger

from src.models.validation_models import ValidationResult, SecurityConfig

# Rate limiting for validation attempts
validation_attempts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
VALIDATION_RATE_LIMIT = 50  # Max validation attempts per IP per minute

# Security patterns - comprehensive XSS and injection prevention
DANGEROUS_PATTERNS = [
    # Script injection
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'vbscript:',
    r'data:text/html',
    r'data:application/',
    
    # Event handlers
    r'on\w+\s*=',
    r'@import',
    r'expression\s*\(',
    
    # SQL injection patterns
    r'union\s+select',
    r'drop\s+table',
    r'insert\s+into',
    r'delete\s+from',
    r'update\s+set',
    r'exec\s*\(',
    r'xp_cmdshell',
    
    # Command injection
    r'[;&|`]',
    r'\$\(',
    r'wget\s',
    r'curl\s',
    r'nc\s',
    r'netcat',
    
    # Path traversal
    r'\.\./.*',
    r'\.\.\\.*',
    
    # LDAP injection
    r'[()=*!&|]',
    
    # NoSQL injection
    r'\$where',
    r'\$ne',
    r'\$gt',
    r'\$regex',
]

# Allowed HTML tags for content sanitization
ALLOWED_HTML_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
ALLOWED_HTML_ATTRIBUTES = {}


def check_rate_limit(identifier: str, limit: int = VALIDATION_RATE_LIMIT) -> bool:
    """Check if validation rate limit is exceeded."""
    now = datetime.utcnow()
    minute_ago = now - timedelta(minutes=1)
    
    # Clean old entries
    attempts = validation_attempts[identifier]
    while attempts and attempts[0] < minute_ago:
        attempts.popleft()
    
    # Check rate limit
    if len(attempts) >= limit:
        logger.warning(f"Rate limit exceeded for {identifier}", extra={
            'identifier': identifier,
            'attempts': len(attempts),
            'limit': limit,
            'security_event': True
        })
        return False
    
    # Record attempt
    attempts.append(now)
    return True


def calculate_entropy(text: str) -> float:
    """Calculate Shannon entropy of text for anomaly detection."""
    if not text:
        return 0.0
    
    # Count character frequencies
    char_counts = defaultdict(int)
    for char in text:
        char_counts[char] += 1
    
    # Calculate entropy
    text_len = len(text)
    entropy = 0.0
    
    for count in char_counts.values():
        probability = count / text_len
        if probability > 0:
            entropy -= probability * (probability.bit_length() - 1)
    
    return entropy


def detect_threats(content: str, strict_mode: bool = True) -> List[str]:
    """Detect potential security threats in content."""
    threats = []
    content_lower = content.lower()
    
    # Check against dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, content_lower, re.IGNORECASE | re.MULTILINE):
            threats.append(f"Detected potential injection: {pattern[:20]}...")
    
    # Check for suspicious character sequences
    if re.search(r'[<>"\'].*[<>"\']', content):
        threats.append("Multiple quote/bracket characters detected")
    
    # Check for encoded payloads
    if '%' in content and re.search(r'%[0-9a-fA-F]{2}', content):
        threats.append("URL encoded content detected")
    
    # Check for base64-like patterns
    if re.search(r'[A-Za-z0-9+/]{20,}={0,2}', content):
        threats.append("Base64-like encoding detected")
    
    # Check for excessive length (potential DoS)
    if len(content) > 10000:
        threats.append("Unusually long input detected")
    
    if strict_mode:
        # Additional strict checks
        if re.search(r'[^\x20-\x7E]', content):
            threats.append("Non-printable characters detected")
        
        if content.count('\n') > 50:
            threats.append("Excessive line breaks detected")
    
    return threats


def sanitize_content(content: str, allow_html: bool = False) -> str:
    """Sanitize content with comprehensive security filtering."""
    if not content:
        return ""
    
    # HTML escape first
    sanitized = html.escape(content)
    
    if allow_html:
        # Use bleach for safe HTML sanitization
        sanitized = bleach.clean(
            content,
            tags=ALLOWED_HTML_TAGS,
            attributes=ALLOWED_HTML_ATTRIBUTES,
            strip=True
        )
    
    # Remove null bytes and control characters
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
    
    # Normalize whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    return sanitized


async def validate_user_input(
    content: str,
    identifier: str = "anonymous",
    config: Optional[SecurityConfig] = None
) -> ValidationResult:
    """Async user input validation with security hardening."""
    start_time = datetime.utcnow()
    config = config or SecurityConfig()
    
    result = ValidationResult()
    
    # Rate limiting check
    if config.rate_limit_enabled and not check_rate_limit(identifier):
        result.is_valid = False
        result.errors.append("Rate limit exceeded")
        result.security_score = 0
        return result
    
    # Basic validation
    if not config.allow_empty and not content.strip():
        result.is_valid = False
        result.errors.append("Content cannot be empty")
        return result
    
    content_len = len(content)
    if content_len < config.min_length:
        result.is_valid = False
        result.errors.append(f"Content must be at least {config.min_length} characters")
    
    if content_len > config.max_length:
        result.is_valid = False
        result.errors.append(f"Content must not exceed {config.max_length} characters")
        result.security_score -= 20
    
    # Security threat detection
    threats = detect_threats(content, config.strict_mode)
    result.detected_threats = threats
    
    if threats:
        result.security_score -= len(threats) * 15
        result.warnings.extend(threats)
        
        # Log security events
        logger.warning("Security threats detected in user input", extra={
            'identifier': identifier,
            'threats': threats,
            'content_hash': hashlib.sha256(content.encode()).hexdigest()[:16],
            'security_event': True
        })
    
    # Entropy analysis
    if config.check_entropy:
        entropy = calculate_entropy(content)
        result.entropy_score = entropy
        
        # Very high entropy might indicate encoded payloads
        if entropy > 7.0:
            result.security_score -= 10
            result.warnings.append("High entropy content detected")
    
    # Content sanitization
    result.sanitized_content = sanitize_content(content, config.allow_html)
    
    # Final security score adjustment
    if result.security_score < 50:
        result.is_valid = False
        result.errors.append("Content failed security validation")
    
    # Performance tracking
    end_time = datetime.utcnow()
    result.processing_time = (end_time - start_time).total_seconds()
    
    return result


def validate_user_input_sync(
    content: str,
    min_length: int = 1,
    max_length: int = 5000,
    allow_empty: bool = False,
    identifier: str = "anonymous"
) -> Dict[str, Any]:
    """Legacy sync validation - use validate_user_input instead."""
    config = SecurityConfig(
        min_length=min_length,
        max_length=max_length,
        allow_empty=allow_empty
    )
    
    # Run async validation in sync context
    async def _async_validate():
        return await validate_user_input(content, identifier, config)
    
    result = asyncio.run(_async_validate())
    
    # Convert to legacy format
    return {
        "is_valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "sanitized_content": result.sanitized_content,
        "security_score": result.security_score
    }



async def validate_email_address(email: str, identifier: str = "anonymous") -> ValidationResult:
    """Email validation with security checks."""
    result = ValidationResult()
    
    if not check_rate_limit(f"email_{identifier}"):
        result.is_valid = False
        result.errors.append("Rate limit exceeded")
        return result
    
    try:
        # Basic format validation
        validated_email = validate_email(email)
        result.sanitized_content = validated_email.email
        
        # Additional security checks
        domain = validated_email.domain
        
        # Check for suspicious domains
        suspicious_domains = ['tempmail', 'guerrillamail', '10minutemail', 'throwaway']
        if any(suspicious in domain.lower() for suspicious in suspicious_domains):
            result.warnings.append("Temporary email service detected")
            result.security_score -= 20
        
        # Check for unusual characters
        if re.search(r'[^\w@.\-+]', email):
            result.warnings.append("Unusual characters in email")
            result.security_score -= 10
        
    except EmailNotValidError as e:
        result.is_valid = False
        result.errors.append(str(e))
        result.security_score = 0
    
    return result


def validate_email_address_sync(email: str) -> Dict[str, Any]:
    """Legacy email validation - use validate_email_address instead."""
    result = asyncio.run(validate_email_address(email))
    
    return {
        "is_valid": result.is_valid,
        "normalized_email": result.sanitized_content,
        "errors": result.errors,
        "security_score": result.security_score
    }


async def validate_password_strength(password: str, identifier: str = "anonymous") -> ValidationResult:
    """Password validation with comprehensive security analysis."""
    result = ValidationResult()
    
    if not check_rate_limit(f"password_{identifier}"):
        result.is_valid = False
        result.errors.append("Rate limit exceeded")
        return result
    
    # Length validation
    if len(password) < 8:
        result.is_valid = False
        result.errors.append("Password must be at least 8 characters long")
    
    # Character variety checks
    has_lower = bool(re.search(r'[a-z]', password))
    has_upper = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    strength_score = 0
    suggestions = []
    
    if has_lower:
        strength_score += 1
    else:
        suggestions.append("Add lowercase letters")
    
    if has_upper:
        strength_score += 1
    else:
        suggestions.append("Add uppercase letters")
    
    if has_digit:
        strength_score += 1
    else:
        suggestions.append("Add numbers")
    
    if has_special:
        strength_score += 1
    else:
        suggestions.append("Add special characters")
    
    # Length bonus
    if len(password) >= 12:
        strength_score += 1
    if len(password) >= 16:
        strength_score += 1
    
    # Security threat detection
    threats = []
    
    # Common weak patterns
    weak_patterns = [
        (r'123456', "Sequential numbers"),
        (r'password', "Contains 'password'"),
        (r'qwerty', "Keyboard pattern"),
        (r'abc123', "Simple pattern"),
        (r'(\w)\1{2,}', "Repeated characters"),
        (r'(password|admin|user|login)', "Common words"),
    ]
    
    for pattern, description in weak_patterns:
        if re.search(pattern, password, re.IGNORECASE):
            strength_score = max(0, strength_score - 2)
            threats.append(description)
    
    # Entropy analysis
    entropy = calculate_entropy(password)
    result.entropy_score = entropy
    
    if entropy < 2.5:
        threats.append("Low entropy (predictable)")
        strength_score = max(0, strength_score - 1)
    
    # Dictionary word detection (simplified)
    common_words = ['password', 'admin', 'user', 'login', 'welcome', 'secret']
    for word in common_words:
        if word.lower() in password.lower():
            threats.append(f"Contains common word: {word}")
            strength_score = max(0, strength_score - 1)
    
    result.detected_threats = threats
    result.security_score = min(100, strength_score * 15)
    
    if strength_score < 3:
        result.is_valid = False
        result.errors.append("Password is too weak")
    
    if suggestions:
        result.warnings.extend(suggestions)
    
    return result


def validate_password_strength_sync(password: str) -> Dict[str, Any]:
    """Legacy password validation - use validate_password_strength instead."""
    result = asyncio.run(validate_password_strength(password))
    
    return {
        "is_valid": result.is_valid,
        "strength_score": result.security_score // 15,  # Convert to 0-6 scale
        "errors": result.errors,
        "suggestions": result.warnings,
        "security_score": result.security_score
    }


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Filename sanitization with security hardening."""
    if not filename:
        return 'unnamed_file'
    
    # Remove dangerous characters and patterns
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Prevent directory traversal
    sanitized = sanitized.replace('..', '_')
    
    # Remove null bytes and control characters
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
    
    # Limit length while preserving extension
    if len(sanitized) > max_length:
        parts = sanitized.rsplit('.', 1)
        if len(parts) == 2:
            name, ext = parts
            max_name_len = max_length - len(ext) - 1
            sanitized = name[:max_name_len] + '.' + ext
        else:
            sanitized = sanitized[:max_length]
    
    # Ensure we have something
    return sanitized or 'unnamed_file'


async def validate_session_data(data: Dict[str, Any], identifier: str = "anonymous") -> ValidationResult:
    """Session data validation with security checks."""
    result = ValidationResult()
    
    if not check_rate_limit(f"session_{identifier}"):
        result.is_valid = False
        result.errors.append("Rate limit exceeded")
        return result
    
    # Required fields validation
    required_fields = ['user_id', 'session_id']
    for field in required_fields:
        if field not in data:
            result.is_valid = False
            result.errors.append(f"Missing required field: {field}")
    
    # Validate user_id format (should be UUID-like)
    if 'user_id' in data:
        user_id = data['user_id']
        if not isinstance(user_id, str):
            result.is_valid = False
            result.errors.append("user_id must be a string")
        elif not re.match(r'^[a-f0-9\-]{10,}$', user_id.lower()):
            result.security_score -= 20
            result.warnings.append("user_id format is suspicious")
    
    # Validate session_id
    if 'session_id' in data:
        session_id = data['session_id']
        if not isinstance(session_id, str) or len(session_id) < 10:
            result.is_valid = False
            result.errors.append("Invalid session_id format")
    
    # Validate input content if present
    if 'input' in data:
        input_result = await validate_user_input(data['input'], identifier)
        if not input_result.is_valid:
            result.is_valid = False
            result.errors.extend(input_result.errors)
        result.warnings.extend(input_result.warnings)
        result.detected_threats.extend(input_result.detected_threats)
        result.security_score = min(result.security_score, input_result.security_score)
    
    # Validate metadata if present
    if 'metadata' in data:
        metadata = data['metadata']
        if not isinstance(metadata, dict):
            result.warnings.append("metadata should be a dictionary")
        elif len(str(metadata)) > 1000:
            result.warnings.append("metadata is unusually large")
            result.security_score -= 10
    
    return result


def validate_session_data_sync(data: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy session validation - use validate_session_data instead."""
    result = asyncio.run(validate_session_data(data))
    
    return {
        "is_valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "security_score": result.security_score
    }


class JSONValidator:
    """JSON schema validator with security features."""
    
    def __init__(self, schema: Dict[str, Any], strict_mode: bool = True):
        self.schema = schema
        self.strict_mode = strict_mode
    
    async def validate(self, data: Any, identifier: str = "anonymous") -> ValidationResult:
        """Validate JSON data against schema with security checks."""
        result = ValidationResult()
        
        if not check_rate_limit(f"json_{identifier}"):
            result.is_valid = False
            result.errors.append("Rate limit exceeded")
            return result
        
        # Check for deeply nested structures (DoS prevention)
        if self._check_nesting_depth(data) > 10:
            result.is_valid = False
            result.errors.append("Data structure too deeply nested")
            result.security_score = 0
            return result
        
        # Check total data size
        data_size = len(str(data))
        if data_size > 100000:  # 100KB limit
            result.is_valid = False
            result.errors.append("Data size too large")
            result.security_score = 0
            return result
        
        # Validate against schema
        self._validate_against_schema(data, self.schema, result, "")
        
        return result
    
    def _check_nesting_depth(self, obj: Any, depth: int = 0) -> int:
        """Check nesting depth to prevent DoS attacks."""
        if depth > 20:  # Hard limit
            return depth
        
        if isinstance(obj, dict):
            return max([self._check_nesting_depth(v, depth + 1) for v in obj.values()] or [depth])
        elif isinstance(obj, list):
            return max([self._check_nesting_depth(item, depth + 1) for item in obj] or [depth])
        else:
            return depth
    
    def _validate_against_schema(self, data: Any, schema: Dict[str, Any], 
                                result: ValidationResult, path: str):
        """Validate data against schema recursively."""
        if not isinstance(schema, dict):
            return
        
        for field_name, field_schema in schema.items():
            field_path = f"{path}.{field_name}" if path else field_name
            
            if field_name not in data:
                if field_schema.get("required", False):
                    result.is_valid = False
                    result.errors.append(f"Required field {field_path} is missing")
                continue
            
            value = data[field_name]
            expected_type = field_schema.get("type")
            
            # Type validation
            if expected_type:
                if not self._validate_type(value, expected_type):
                    result.is_valid = False
                    result.errors.append(f"Field {field_path} must be of type {expected_type}")
                    continue
            
            # String validation with security checks
            if expected_type == "string" and isinstance(value, str):
                # Check for suspicious content
                threats = detect_threats(value)
                if threats:
                    result.detected_threats.extend([f"{field_path}: {threat}" for threat in threats])
                    result.security_score -= len(threats) * 5
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type."""
        type_mapping = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, skip validation
        
        return isinstance(value, expected_python_type)


def validate_json_structure(data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy JSON validation - use JSONValidator instead."""
    validator = JSONValidator(schema)
    result = asyncio.run(validator.validate(data))
    
    return {
        "is_valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "security_score": result.security_score
    }


def get_validation_metrics() -> Dict[str, Any]:
    """Get validation metrics for monitoring."""
    return {
        "total_validation_attempts": sum(len(attempts) for attempts in validation_attempts.values()),
        "unique_identifiers": len(validation_attempts),
        "rate_limited_identifiers": [
            identifier for identifier, attempts in validation_attempts.items()
            if len(attempts) >= VALIDATION_RATE_LIMIT
        ]
    }


def reset_validation_metrics():
    """Reset validation metrics (useful for testing)."""
    global validation_attempts
    validation_attempts.clear()


# Export validation functions
__all__ = [
    'validate_user_input',
    'validate_email_address', 
    'validate_password_strength',
    'validate_session_data',
    'JSONValidator',
    'sanitize_content',
    'sanitize_filename',
    'get_validation_metrics',
    'reset_validation_metrics',
    'validate_json_structure'
]
