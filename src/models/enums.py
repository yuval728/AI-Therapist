from enum import Enum

class AttackType(str, Enum):
    SAFE = "safe"
    BLOCKED = "blocked"
    INJECTED = "prompt_injection"
    PII_FOUND = "pii_found"
    UNSAFE_OUTPUT = "unsafe_output"
