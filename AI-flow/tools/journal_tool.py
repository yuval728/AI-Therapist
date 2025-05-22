from litellm import completion
from pydantic import BaseModel


class JournalAnalyzer(BaseModel):
    journal_entry: str
    
    
def journal_tool(entry: str) -> str:
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
    
    response = completion(model="gemini/gemini-2.0-flash", messages=messages, temperature=0.0, response_format=JournalAnalyzer)
    return response["choices"][0]["message"]["content"].get("journal_entry", "").strip()
