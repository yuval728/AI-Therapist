from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase import create_client, Client
from typing import Dict, List, Optional
from src.memory.state import TherapyState
from uuid import uuid4
import datetime
import os
import dotenv
import tiktoken
from loguru import logger

dotenv.load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key must be set in environment variables.")


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize vector store with Google Gemini embeddings
# Requires environment variable GOOGLE_API_KEY to be set.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY must be set in environment variables for Gemini embeddings.")

gemini_embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

vector_store = SupabaseVectorStore(
    client=supabase,
    embedding=gemini_embeddings,
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


def save_to_long_term_memory(user_id: str, content: str, metadata: Optional[Dict] = None):
    """Save content and embedding to Supabase vector store with proper Document construction."""
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

# def save_to_long_term_memory(user_id: str, content: str, metadata: Optional[Dict] = None):
#     """Store both in Supabase DB and vector index with correct user_id."""
#     metadata = metadata or {}

#     # 1. Create metadata
#     document_id = str(uuid4())
#     timestamp = datetime.datetime.utcnow().isoformat()
#     full_metadata = {
#         "timestamp": timestamp,
#         "document_id": document_id,
#         **metadata
#     }

#     # 2. Insert metadata + user_id into Supabase manually
#     insert_response = supabase.table("documents").insert({
#         "user_id": user_id,
#         "content": content,
#         "metadata": full_metadata
#     }).execute()

#     if insert_response.error:
#         raise Exception(f"Supabase insert failed: {insert_response.error}")

#     # 3. Embed and push to SupabaseVectorStore
#     doc = Document(page_content=content, metadata=full_metadata)
#     vector_store.add_documents([doc])  # will match by metadata["document_id"]


def search_long_term_memory(user_id: str, query: str, k: int = 3) -> List[Document]:
    """Search relevant documents from Supabase vector store."""
    results = vector_store.similarity_search(
        query=query, k=k, filter={"user_id": user_id}
    )
    for doc in results:
        print(f"[Memory Hit] {doc.page_content[:80]}... (metadata: {doc.metadata})")
    return results


# === Pruning & Summarization ===
ENCODING = None
def _encoding():
    global ENCODING
    if ENCODING is None:
        try:
            ENCODING = tiktoken.get_encoding("cl100k_base")
        except Exception:
            class Dummy:
                def encode(self, x):
                    return x.split()
            ENCODING = Dummy()
    return ENCODING

def count_tokens(text: str) -> int:
    return len(_encoding().encode(text))

def prune_messages(state: TherapyState, max_tokens: int = 1200) -> TherapyState:
    """If combined message tokens exceed limit, summarize earliest half into state['summary']."""
    messages = state["messages"]
    if not messages:
        return state
    total = 0
    for m in reversed(messages):  # newest first accumulating
        total += count_tokens(m.content)
    if total <= max_tokens:
        return state
    # summarize older half
    cutoff = len(messages)//2
    to_summarize = messages[:cutoff]
    remain = messages[cutoff:]
    summary_text = "\n".join(m.content for m in to_summarize)
    state["summary"] = (state.get("summary") or "") + "\n" + summary_text[:2000]
    state["messages"] = remain
    logger.info(f"memory_pruned tokens={total} new_messages={len(remain)}")
    return state


# TODO: Integrate this
def recent_filter(doc: Document, days=30) -> bool:
    try:
        ts = datetime.datetime.fromisoformat(doc.metadata.get("timestamp", ""))
        return ts >= datetime.utcnow() - datetime.timedelta(days=days)
    except Exception as e:
        print(f"Error parsing timestamp: {e}")
        return True
