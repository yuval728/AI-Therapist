# memory/memory_manager.py

from typing import Dict, List
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os

# === SHORT-TERM MEMORY SETUP ===
# Production-grade persistence using SQLite (can be swapped with Supabase/Redis)
checkpointer = SqliteSaver("./chat_memory.sqlite")

# === LONG-TERM MEMORY SETUP ===
CHROMA_DIR = "./vector_store"
os.makedirs(CHROMA_DIR, exist_ok=True)

embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
vector_store = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding_model)

# === SHORT-TERM MEMORY FUNCTIONS ===
def initialize_state() -> Dict:
    """Initializes an empty state for the LangGraph app with memory."""
    return {"messages": []}

def append_to_memory(state: MessagesState, new_messages: List[BaseMessage]) -> MessagesState:
    """Adds new messages to the memory state."""
    return {"messages": state["messages"] + new_messages}

def get_latest_human_message(state: MessagesState) -> str:
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""

def get_latest_ai_message(state: MessagesState) -> str:
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage):
            return msg.content
    return ""

# === LONG-TERM MEMORY FUNCTIONS ===
def save_to_long_term_memory(user_id: str, content: str, metadata: Dict = None):
    """Saves a message or journal entry into vector memory."""
    metadata = metadata or {}
    document = Document(page_content=content, metadata={"user_id": user_id, **metadata})
    vector_store.add_documents([document])
    vector_store.persist()

def search_long_term_memory(user_id: str, query: str, k: int = 3) -> List[Document]:
    """Searches for relevant documents in vector memory."""
    results = vector_store.similarity_search(query, k=k, filter={"user_id": user_id})
    return results
