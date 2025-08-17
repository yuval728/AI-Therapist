from pydantic import BaseModel
import json
from src.config import get_settings
from src.llm_utils import async_completion
settings = get_settings()

class EmotionAnalyzer(BaseModel):
    emotion: str

async def emotion_tool(text: str) -> str:
    """
    Uses LiteLLM to classify the user's emotional state.
    Returns one-word emotion like 'sad', 'anxious', 'angry', etc.
    """
    messages = [
        {"role": "system", "content": "You are an expert emotional classifier."},
        {"role": "user", "content": f"What emotion is being expressed in this message: '{text}'? Reply with one word only."}
    ]

    response = await async_completion(model=settings.model_light, messages=messages, temperature=settings.temperature_classifiers, response_format=EmotionAnalyzer)
    response = response["choices"][0]["message"]["content"]
    response = json.loads(response)
    
    return response.get("emotion", "").strip().lower()
