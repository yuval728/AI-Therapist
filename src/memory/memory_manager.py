from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from supabase import create_client, Client
from typing import Dict, List, Optional
from src.memory.state import TherapyState
from uuid import uuid4
import datetime
import os
import dotenv

dotenv.load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key must be set in environment variables.")


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize vector store
vector_store = SupabaseVectorStore(
    client=supabase,
    embedding=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),
    table_name="documents",
    query_name="match_documents",
)


# === SHORT-TERM MEMORY FUNCTIONS ===
def append_to_memory(
    state: TherapyState, message: BaseMessage, role: str = "user"
) -> TherapyState:
    """Appends a new message to the short-term memory."""

    """Appends message to Supabase memory_logs."""
    user_id = state["user_id"]
    supabase.table("memory_logs").insert(
        {
            "user_id": user_id,
            "role": role,
            "content": message.content,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "emotion": state.get("emotion"),
            "is_crisis": state.get("is_crisis"),
            "mode": state.get("mode"),
            "journal_entry": state.get("journal_entry"),
            "attack": state.get("attack"),
        }
    ).execute()
    state["messages"].append(message)
    return state


def get_memory(
    state: TherapyState, limit: int = 6, from_db: bool = True
) -> List[BaseMessage]:
    """Retrieve last N messages from database or state."""
    if not from_db:
        # If not from DB, return messages from state
        return state["messages"][-limit:]

    user_id = state["user_id"]
    response = (
        supabase.table("memory_logs")
        .select("content, role")
        .eq("user_id", user_id)
        .order("timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    messages = []
    for row in reversed(response.data):
        role = row["role"]
        content = row["content"]
        if role == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
    return messages


def save_to_long_term_memory(
    user_id: str, content: str, metadata: Optional[Dict] = None
):
    """Save content and embedding to Supabase."""
    metadata = metadata or {}
    document = Document(
        page_content=content,
        metadata={
            "user_id": user_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "document_id": str(uuid4()),
            **metadata,
        },
    )
    vector_store.add_documents([document])


def search_long_term_memory(user_id: str, query: str, k: int = 3) -> List[Document]:
    """Search relevant documents from Supabase vector store."""
    results = vector_store.similarity_search(
        query=query, k=k, filter={"user_id": user_id}
    )
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
