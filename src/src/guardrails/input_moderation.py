import re

# 🛡️ Input Moderation Check
def contains_unsafe_content(text: str) -> bool:
    """
    Returns True if the input contains unsafe or flagged content.
    """
    # Simple keyword-based filter — you can use OpenAI/Anthropic moderation APIs here.
    unsafe_keywords = [
        "kill myself", "suicide", "abuse", "rape", "murder",
        "hate speech", "bomb", "school shooting", "cut myself"
        "terrorism", "kill", "hurt", "self-harm", "violence",
    ]
    text = text.lower()
    return any(word in text for word in unsafe_keywords)


# 🧪 Prompt Injection Detector
def detect_prompt_injection(text: str) -> bool:
    """
    Detect basic prompt injection attempts using keyword matching.
    """
    injection_patterns = [
        r"ignore (the )?previous", r"disregard (the )?above",
        r"act as", r"simulate", r"pretend to", r"bypass",
        r"jailbreak", r"you are now"
    ]
    return any(re.search(pattern, text.lower()) for pattern in injection_patterns)


# 🧯 Output Safety Validator
def contains_dangerous_response(text: str) -> bool:
    """
    Detect unsafe AI responses, e.g., that could be interpreted as medical advice,
    harmful instructions, or misinformation.
    """
    flagged_phrases = [
        "you should just give up", "go ahead and hurt yourself",
        "I diagnose you", "take medication", "here’s how to",
        "no one cares", "you are worthless"
    ]
    return any(phrase in text.lower() for phrase in flagged_phrases)
