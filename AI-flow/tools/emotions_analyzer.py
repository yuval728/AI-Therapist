from litellm import completion
from pydantic import BaseModel
import json

class EmotionAnalyzer(BaseModel):
    emotion: str

def emotion_tool(text: str) -> str:
    """
    Uses LiteLLM to classify the user's emotional state.
    Returns one-word emotion like 'sad', 'anxious', 'angry', etc.
    """
    messages = [
        {"role": "system", "content": "You are an expert emotional classifier."},
        {"role": "user", "content": f"What emotion is being expressed in this message: '{text}'? Reply with one word only."}
    ]

    response = completion(model="gemini/gemini-2.0-flash-lite", messages=messages, temperature=0.0, response_format=EmotionAnalyzer)
    response = response["choices"][0]["message"]["content"]
    response = json.loads(response)
    
    return response.get("emotion", "").strip().lower()
