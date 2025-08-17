from pydantic import BaseModel
import json
from src.config import get_settings
from src.llm_utils import async_completion
settings = get_settings()

class CrisisAnalyzer(BaseModel):
    crisis: bool


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

    response = await async_completion(
        model=settings.model_light,
        messages=messages,
        temperature=settings.temperature_classifiers,
        response_format=CrisisAnalyzer,
    )
    response = response["choices"][0]["message"]["content"]
    response = json.loads(response)
    return response.get("crisis", False)
