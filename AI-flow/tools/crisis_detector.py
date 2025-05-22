from litellm import completion
from pydantic import BaseModel


class CrisisAnalyzer(BaseModel):
    crisis: bool
    
    
def crisis_tool(text: str) -> bool:
    """
    Uses LiteLLM to detect if the message contains a mental health crisis.
    Returns True if the message indicates suicidal thoughts, self-harm, or emergency.
    """
    messages = [
        {"role": "system", "content": "You are a mental health safety checker."},
        {"role": "user", "content": f"""
Analyze this message for signs of crisis:
'{text}'

If the message mentions suicide, self-harm, or extreme emotional distress, respond with ONLY True.
If it's safe or neutral, respond with ONLY False.
"""}
    ]

    response = completion(model="gemini/gemini-2.0-flash-lite", messages=messages, temperature=0.0, response_format=CrisisAnalyzer)
    return response["choices"][0]["message"]["content"].get("crisis", False)
