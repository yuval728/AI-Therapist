from src.config.config import get_settings
from src.core.llm_utils import async_completion
settings = get_settings()
# import json

# class JournalAnalyzer(BaseModel):
#     journal_entry: str
    
    
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
    
    response = await async_completion(model=settings.model_chat, messages=messages, temperature=settings.temperature_chat)
    response = response["choices"][0]["message"]["content"]
    return response
    
