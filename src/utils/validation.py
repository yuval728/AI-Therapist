"""Input validation utilities for the AI therapist application."""
import re
from typing import Any, Dict, List, Optional, Union
from pydantic import ValidationError
from email_validator import validate_email, EmailNotValidError


def validate_user_input(
    content: str,
    min_length: int = 1,
    max_length: int = 5000,
    allow_empty: bool = False
) -> Dict[str, Any]:
    """Validate user input content with safety checks."""
    result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "sanitized_content": content.strip()
    }
    
    if not allow_empty and not content.strip():
        result["is_valid"] = False
        result["errors"].append("Content cannot be empty")
        return result
    
    if len(content) < min_length:
        result["is_valid"] = False
        result["errors"].append(f"Content must be at least {min_length} characters")
    
    if len(content) > max_length:
        result["is_valid"] = False
        result["errors"].append(f"Content must not exceed {max_length} characters")
    
    # Check for potential security issues
    suspicious_patterns = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'data:text/html',  # Data URLs
        r'vbscript:',  # VBScript
        r'on\w+\s*=',  # Event handlers
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            result["warnings"].append("Content contains potentially unsafe elements")
            break
    
    return result


def validate_email_address(email: str) -> Dict[str, Any]:
    """Validate email address format and deliverability."""
    result = {
        "is_valid": True,
        "normalized_email": None,
        "errors": []
    }
    
    try:
        validated_email = validate_email(email)
        result["normalized_email"] = validated_email.email
    except EmailNotValidError as e:
        result["is_valid"] = False
        result["errors"].append(str(e))
    
    return result


def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength and security requirements."""
    result = {
        "is_valid": True,
        "strength_score": 0,
        "errors": [],
        "suggestions": []
    }
    
    if len(password) < 8:
        result["is_valid"] = False
        result["errors"].append("Password must be at least 8 characters long")
    else:
        result["strength_score"] += 1
    
    if len(password) >= 12:
        result["strength_score"] += 1
    
    # Check for character variety
    has_lower = bool(re.search(r'[a-z]', password))
    has_upper = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    if has_lower:
        result["strength_score"] += 1
    else:
        result["suggestions"].append("Add lowercase letters")
    
    if has_upper:
        result["strength_score"] += 1
    else:
        result["suggestions"].append("Add uppercase letters")
    
    if has_digit:
        result["strength_score"] += 1
    else:
        result["suggestions"].append("Add numbers")
    
    if has_special:
        result["strength_score"] += 1
    else:
        result["suggestions"].append("Add special characters")
    
    # Check for common weak patterns
    weak_patterns = [
        r'123456',
        r'password',
        r'qwerty',
        r'abc123',
        r'(\w)\1{2,}',  # Repeated characters
    ]
    
    for pattern in weak_patterns:
        if re.search(pattern, password, re.IGNORECASE):
            result["strength_score"] = max(0, result["strength_score"] - 2)
            result["suggestions"].append("Avoid common patterns and repeated characters")
            break
    
    # Final validation
    if result["strength_score"] < 3:
        result["is_valid"] = False
        result["errors"].append("Password is too weak")
    
    return result


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations."""
    # Remove or replace dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        max_name_len = 255 - len(ext) - 1 if ext else 255
        sanitized = name[:max_name_len] + ('.' + ext if ext else '')
    
    return sanitized or 'unnamed_file'


def validate_session_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate therapy session data structure."""
    result = {
        "is_valid": True,
        "errors": [],
        "warnings": []
    }
    
    required_fields = ['user_id', 'session_id', 'input']
    for field in required_fields:
        if field not in data:
            result["is_valid"] = False
            result["errors"].append(f"Missing required field: {field}")
    
    # Validate user_id format (UUID-like)
    if 'user_id' in data:
        user_id = data['user_id']
        if not isinstance(user_id, str) or len(user_id) < 10:
            result["is_valid"] = False
            result["errors"].append("Invalid user_id format")
    
    # Validate input content
    if 'input' in data:
        input_validation = validate_user_input(data['input'])
        if not input_validation["is_valid"]:
            result["is_valid"] = False
            result["errors"].extend(input_validation["errors"])
        result["warnings"].extend(input_validation["warnings"])
    
    return result


def validate_json_structure(data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Validate JSON data against a simple schema."""
    result = {
        "is_valid": True,
        "errors": []
    }
    
    def validate_field(value: Any, field_schema: Dict[str, Any], field_name: str = ""):
        if "type" in field_schema:
            expected_type = field_schema["type"]
            if expected_type == "string" and not isinstance(value, str):
                result["errors"].append(f"Field {field_name} must be a string")
                result["is_valid"] = False
            elif expected_type == "number" and not isinstance(value, (int, float)):
                result["errors"].append(f"Field {field_name} must be a number")
                result["is_valid"] = False
            elif expected_type == "boolean" and not isinstance(value, bool):
                result["errors"].append(f"Field {field_name} must be a boolean")
                result["is_valid"] = False
            elif expected_type == "array" and not isinstance(value, list):
                result["errors"].append(f"Field {field_name} must be an array")
                result["is_valid"] = False
            elif expected_type == "object" and not isinstance(value, dict):
                result["errors"].append(f"Field {field_name} must be an object")
                result["is_valid"] = False
        
        if "required" in field_schema and field_schema["required"] and value is None:
            result["errors"].append(f"Field {field_name} is required")
            result["is_valid"] = False
    
    if isinstance(schema, dict) and isinstance(data, dict):
        for field_name, field_schema in schema.items():
            if field_name in data:
                validate_field(data[field_name], field_schema, field_name)
            elif field_schema.get("required", False):
                result["errors"].append(f"Required field {field_name} is missing")
                result["is_valid"] = False
    
    return result
