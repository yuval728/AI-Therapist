"""Consolidated therapy tools for analysis and processing."""
from pydantic import BaseModel
import json
from src.config import get_settings
from src.core.llm_utils import get_completion
from src.models.enums import EmotionType, CrisisLevel, MessageType

settings = get_settings()


class CrisisAnalyzer(BaseModel):
    crisis: CrisisLevel


class EmotionAnalyzer(BaseModel):
    emotion: EmotionType


async def crisis_tool(text: str) -> CrisisLevel:
    """
    Uses LiteLLM to detect if the message contains a mental health crisis.
    Returns the severity level of the crisis.
    """
    messages = [
        {"role": "system", "content": "You are a mental health safety checker."},
        {
            "role": "user",
            "content": f"""
Analyze this message for signs of crisis:
'{text}'
Respond with only: 'none', 'low', 'moderate', 'high', or 'critical' based on the severity of crisis indicators.
""",
        },
    ]

    response = await get_completion(
        model=settings.models.light_model,
        messages=messages,
        temperature=settings.models.temperature_classifiers,
        response_format=CrisisAnalyzer,
    )
    response = response["choices"][0]["message"]["content"]
    response = json.loads(response)
    return response["crisis"]


async def emotion_tool(text: str) -> EmotionType:
    """
    Uses LiteLLM to classify the user's emotional state.
    Returns one-word emotion like 'sad', 'anxious', 'angry', etc.
    """
    messages = [
        {"role": "system", "content": "You are an expert emotional classifier."},
        {"role": "user", "content": f"What emotion is being expressed in this message: '{text}'? Reply with only the primary emotion: happy, sad, angry, anxious, fearful, surprised, disgusted, neutral, confused, excited, calm, frustrated, hopeful, lonely, or overwhelmed."}
    ]

    response = await get_completion(
        model=settings.models.light_model, 
        messages=messages, 
        temperature=settings.models.temperature_classifiers, 
        response_format=EmotionAnalyzer
    )
    response = response["choices"][0]["message"]["content"]
    response = json.loads(response)
    return response["emotion"]




async def journal_tool(entry: str) -> str:
    """
    Reflects on a user's journal entry and provides a supportive, therapeutic response.
    Can be used for journaling, mood tracking, or self-awareness.
    """
    messages = [
        {"role": "system", "content": (
            "You are an empathetic AI therapist. A user has written a journal entry. "
            "Read it, reflect on the feelings expressed, and provide a thoughtful and supportive response. "
            "End with a gentle follow-up question to encourage continued journaling."
        )},
        {"role": "user", "content": f"Journal Entry:\n{entry}"}
    ]
    
    response = await get_completion(
        model=settings.models.chat_model, 
        messages=messages, 
        temperature=settings.models.temperature_chat
    )
    response = response["choices"][0]["message"]["content"]
    return response