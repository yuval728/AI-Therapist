from typing import TypedDict, List, Optional
from langchain_core.messages import BaseMessage


class TherapyState(TypedDict):
    input: str  # latest user input
    messages: List[BaseMessage]  # short-term memory (chat history)
    response: Optional[str]  # latest assistant response
    relevant_memories: Optional[List[str]]  # vector recall results
    emotion: Optional[str]  # output of emotion analyzer
    is_crisis: Optional[bool]  # output of crisis detection
    mode: Optional[str]  # 'chat' or 'journal' (from classifier)
    journal_entry: Optional[str]  # if journal, store full entry