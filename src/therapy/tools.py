"""Consolidated therapy tools for analysis and processing."""
from pydantic import BaseModel
import json
from src.config import get_settings
from src.core.llm_utils import get_completion

settings = get_settings()


class CrisisAnalyzer(BaseModel):
    crisis: bool


class EmotionAnalyzer(BaseModel):
    emotion: str


async def crisis_tool(text: str) -> bool:
    """
    Uses LiteLLM to detect if the message contains a mental health crisis.
    Returns True if the message indicates suicidal thoughts, self-harm, or emergency.
    """
    messages = [
        {"role": "system", "content": "You are a mental health safety checker."},
        {
            "role": "user",
            "content": f"""
Analyze this message for signs of crisis:
'{text}'

If the message mentions suicide, self-harm, or extreme emotional distress, respond with ONLY True.
If it's safe or neutral, respond with ONLY False.
""",
        },
    ]

    response = await get_completion(
        model=settings.model_light,
        messages=messages,
        temperature=settings.temperature_classifiers,
        response_format=CrisisAnalyzer,
    )
    response = response["choices"][0]["message"]["content"]
    response = json.loads(response)
    return response.get("crisis", False)


async def emotion_tool(text: str) -> str:
    """
    Uses LiteLLM to classify the user's emotional state.
    Returns one-word emotion like 'sad', 'anxious', 'angry', etc.
    """
    messages = [
        {"role": "system", "content": "You are an expert emotional classifier."},
        {"role": "user", "content": f"What emotion is being expressed in this message: '{text}'? Reply with one word only."}
    ]

    response = await get_completion(
        model=settings.model_light, 
        messages=messages, 
        temperature=settings.temperature_classifiers, 
        response_format=EmotionAnalyzer
    )
    response = response["choices"][0]["message"]["content"]
    response = json.loads(response)
    
    return response.get("emotion", "").strip().lower()


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
        model=settings.model_chat, 
        messages=messages, 
        temperature=settings.temperature_chat
    )
    response = response["choices"][0]["message"]["content"]
    return response
