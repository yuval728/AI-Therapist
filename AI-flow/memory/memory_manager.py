# from langgraph.checkpoint.memory import MemorySaver
# from langgraph.store.memory import InMemoryStore
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
from typing import Dict, List
from memory.state import TherapyState
from uuid import uuid4
import datetime


# embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-large-en-v1.5",
    # model_kwargs={"device": "cuda:0"},
    cache_folder="./cache",
)
vector_store = Chroma(
    persist_directory="./vector_store", embedding_function=embedding_model
)


# === SHORT-TERM MEMORY FUNCTIONS ===
def append_to_memory(
    state: TherapyState, message: BaseMessage, role: str = "user"
) -> TherapyState:
    """Appends a new message to the short-term memory."""
    state["messages"].append(message)
    return state


def get_memory(state: TherapyState) -> List[BaseMessage]:
    """Retrieves the current memory state."""
    return state["messages"][-6:]  # Get the last 6 messages


# # === LONG-TERM MEMORY FUNCTIONS ===
def save_to_long_term_memory(user_id: str, content: str, metadata: Dict = None):
    """Saves a message or journal entry into vector memory."""
    metadata = metadata or {}
    document = Document(
        page_content=content,
        metadata={
            "user_id": user_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "document_id": str(uuid4()),
        },
    )
    vector_store.add_documents([document])
    # vector_store.persist()


def search_long_term_memory(user_id: str, query: str, k: int = 3) -> List[Document]:
    """Searches for relevant documents in vector memory."""
    results = vector_store.similarity_search(query, k=k, filter={"user_id": user_id})
    for doc in results:
        print(f"[Memory Hit] {doc.page_content[:80]}... (metadata: {doc.metadata})")
    return results


# TODO: Integrate this
def recent_filter(doc: Document, days=30) -> bool:
    try:
        ts = datetime.datetime.fromisoformat(doc.metadata.get("timestamp", ""))
        return ts >= datetime.utcnow() - datetime.timedelta(days=days)
    except Exception as e:
        print(f"Error parsing timestamp: {e}")
        return True
