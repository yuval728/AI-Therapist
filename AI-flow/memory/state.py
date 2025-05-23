from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TherapyState(TypedDict):
    user_id: str  # user ID
    input: str  # latest user input
    # messages: Annotated[List[BaseMessage], add_messages]  # short-term memory
    messages: List[BaseMessage]  # short-term memory
    response: Optional[str]  # response from the model
    relevant_memories: Optional[List[str]]  # vector recall results
    emotion: Optional[str]  # output of emotion analyzer
    is_crisis: Optional[bool]  # output of crisis detection
    mode: Optional[str]  # 'chat' or 'journal' (from classifier)
    journal_entry: Optional[str]  # if journal, store full entry