import re

def detect_pii(text: str) -> bool:
    patterns = [
        r"\b\d{3}-\d{2}-\d{4}\b",              # SSN
        r"\b\d{10}\b",                         # Phone numbers
        r"\b\d{5}(-\d{4})?\b",                 # ZIP code
        r"\b[\w.-]+@[\w.-]+\.\w{2,4}\b",       # Email
        r"\b(?:\d[ -]*?){13,16}\b",            # Credit card
    ]
    return any(re.search(p, text) for p in patterns)