from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase import create_client, Client
from src.config import get_settings
from src.models import TherapyState
from src.utils import log_therapy_event, timing_decorator
from typing import Dict, List, Optional, Tuple
from uuid import uuid4
import datetime
import os
import dotenv
import tiktoken
from dataclasses import dataclass

@dataclass
class MemorySearchResult:
    """Structured result for memory searches."""
    documents: List[Document]
    total_found: int
    search_time_ms: float
    query: str
    user_id: str


@dataclass
class MemoryStats:
    """Memory statistics for monitoring."""
    short_term_count: int
    long_term_count: int
    total_tokens: int
    last_pruned: Optional[datetime.datetime]
    summary_length: int


class MemoryManager:
    """Enhanced memory manager with improved organization and monitoring."""
    
    def __init__(self):
        self.settings = get_settings()
        dotenv.load_dotenv()
        
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL") or self.settings.database.supabase_url
        supabase_key = os.getenv("SUPABASE_KEY") or self.settings.database.supabase_key
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase URL and Key must be configured.")
        
        self.supabase = create_client(supabase_url, supabase_key)
        
        # Initialize embeddings
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY must be set for embeddings.")
        
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        self.vector_store = SupabaseVectorStore(
            client=self.supabase,
            embedding=self.embeddings,
            table_name="documents",
            query_name="match_documents",
        )
        
        # Token encoding for pruning
        self._encoding = None
    
    def _get_encoding(self):
        """Get token encoding for text processing."""
        if self._encoding is None:
            try:
                self._encoding = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # Fallback encoding
                class DummyEncoding:
                    def encode(self, text):
                        return text.split()
                self._encoding = DummyEncoding()
        return self._encoding
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self._get_encoding().encode(text))
    
    @timing_decorator("append_to_memory")
    def append_to_memory(
        self, 
        state: TherapyState, 
        message: BaseMessage, 
        role: str = "user"
    ) -> TherapyState:
        """Enhanced memory append with monitoring and error handling."""
        user_id = state["user_id"]
        session_id = state.get("session_id", "default")
        
        try:
            # Insert to database with enhanced metadata
            self.supabase.table("memory_logs").insert({
                "user_id": user_id,
                "session_id": session_id,
                "role": role,
                "content": message.content,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "emotion": state.get("emotion"),
                "emotion_confidence": state.get("emotion_confidence"),
                "is_crisis": state.get("is_crisis"),
                "crisis_level": state.get("crisis_level"),
                "mode": state.get("mode"),
                "journal_entry": state.get("journal_entry"),
                "attack": state.get("attack"),
                "message_length": len(message.content),
                "token_count": self.count_tokens(message.content)
            }).execute()
            
            # Add to state
            state["messages"].append(message)
            
            # Log memory operation
            log_therapy_event(
                event="memory_appended",
                user_id=user_id,
                session_id=session_id,
                role=role,
                message_length=len(message.content),
                total_messages=len(state["messages"])
            )
            
            return state
            
        except Exception as e:
            log_therapy_event(
                event="memory_append_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            # Still add to state even if DB fails
            state["messages"].append(message)
            return state


    @timing_decorator("get_memory")
    def get_memory(
        self, 
        state: TherapyState, 
        limit: int = 6, 
        from_db: bool = True
    ) -> List[BaseMessage]:
        """Enhanced memory retrieval with monitoring."""
        user_id = state["user_id"]
        session_id = state.get("session_id", "default")
        
        if not from_db:
            # Return messages from state
            messages = state["messages"][-limit:]
            log_therapy_event(
                event="memory_retrieved_from_state",
                user_id=user_id,
                session_id=session_id,
                message_count=len(messages)
            )
            return messages

        try:
            response = (
                self.supabase.table("memory_logs")
                .select("content, role, timestamp, emotion, crisis_level")
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
            
            log_therapy_event(
                event="memory_retrieved_from_db",
                user_id=user_id,
                session_id=session_id,
                message_count=len(messages),
                requested_limit=limit
            )
            
            return messages
            
        except Exception as e:
            log_therapy_event(
                event="memory_retrieval_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            # Fallback to state messages
            return state["messages"][-limit:]

    @timing_decorator("save_long_term_memory")
    def save_to_long_term_memory(
        self, 
        user_id: str, 
        content: str, 
        metadata: Optional[Dict] = None
    ) -> bool:
        """Enhanced long-term memory save with monitoring."""
        metadata = metadata or {}
        
        try:
            document = Document(
                page_content=content,
                metadata={
                    "user_id": user_id,
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "document_id": str(uuid4()),
                    "content_length": len(content),
                    "token_count": self.count_tokens(content),
                    **metadata,
                },
            )
            
            self.vector_store.add_documents([document])
            
            log_therapy_event(
                event="long_term_memory_saved",
                user_id=user_id,
                content_length=len(content),
                metadata_keys=list(metadata.keys())
            )
            
            return True
            
        except Exception as e:
            log_therapy_event(
                event="long_term_memory_save_failed",
                user_id=user_id,
                error=str(e)
            )
            return False

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


    @timing_decorator("search_long_term_memory")
    def search_long_term_memory(
        self, 
        user_id: str, 
        query: str, 
        k: int = 3,
        days_filter: int = 30
    ) -> MemorySearchResult:
        """Enhanced long-term memory search with monitoring."""
        import time
        start_time = time.time()
        
        try:
            results = self.vector_store.similarity_search(
                query=query, 
                k=k, 
                filter={"user_id": user_id}
            )
            
            # Filter by recency if specified
            if days_filter:
                cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_filter)
                filtered_results = []
                for doc in results:
                    try:
                        doc_date = datetime.datetime.fromisoformat(
                            doc.metadata.get("timestamp", "")
                        )
                        if doc_date >= cutoff_date:
                            filtered_results.append(doc)
                    except Exception:
                        # Include docs with invalid timestamps
                        filtered_results.append(doc)
                results = filtered_results
            
            search_time = (time.time() - start_time) * 1000
            
            log_therapy_event(
                event="long_term_memory_searched",
                user_id=user_id,
                query_length=len(query),
                results_found=len(results),
                search_time_ms=search_time,
                k_requested=k
            )
            
            return MemorySearchResult(
                documents=results,
                total_found=len(results),
                search_time_ms=search_time,
                query=query,
                user_id=user_id
            )
            
        except Exception as e:
            log_therapy_event(
                event="long_term_memory_search_failed",
                user_id=user_id,
                error=str(e)
            )
            return MemorySearchResult(
                documents=[],
                total_found=0,
                search_time_ms=0,
                query=query,
                user_id=user_id
            )

    @timing_decorator("prune_messages")
    def prune_messages(
        self, 
        state: TherapyState, 
        max_tokens: int = 1200
    ) -> TherapyState:
        """Enhanced message pruning with monitoring."""
        user_id = state["user_id"]
        session_id = state.get("session_id", "default")
        messages = state["messages"]
        
        if not messages:
            return state
        
        # Calculate total tokens
        total_tokens = 0
        for message in reversed(messages):
            total_tokens += self.count_tokens(message.content)
        
        if total_tokens <= max_tokens:
            return state
        
        try:
            # Summarize older half
            cutoff = len(messages) // 2
            to_summarize = messages[:cutoff]
            remaining = messages[cutoff:]
            
            # Create summary
            summary_text = "\n".join(m.content for m in to_summarize)
            truncated_summary = summary_text[:2000]  # Limit summary length
            
            # Update state
            existing_summary = state.get("summary", "")
            state["summary"] = (existing_summary + "\n" + truncated_summary).strip()
            state["messages"] = remaining
            
            # Log pruning event
            log_therapy_event(
                event="memory_pruned",
                user_id=user_id,
                session_id=session_id,
                original_tokens=total_tokens,
                original_messages=len(messages),
                remaining_messages=len(remaining),
                summary_length=len(state["summary"])
            )
            
            return state
            
        except Exception as e:
            log_therapy_event(
                event="memory_pruning_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return state

    def get_memory_stats(self, user_id: str) -> MemoryStats:
        """Get memory statistics for monitoring."""
        try:
            # Get short-term memory count
            short_term_response = (
                self.supabase.table("memory_logs")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .execute()
            )
            short_term_count = short_term_response.count or 0
            
            # Get long-term memory count (approximate)
            long_term_response = (
                self.supabase.table("documents")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .execute()
            )
            long_term_count = long_term_response.count or 0
            
            return MemoryStats(
                short_term_count=short_term_count,
                long_term_count=long_term_count,
                total_tokens=0,  # Would need to calculate
                last_pruned=None,  # Would need to track
                summary_length=0  # Would need to calculate
            )
            
        except Exception as e:
            log_therapy_event(
                event="memory_stats_failed",
                user_id=user_id,
                error=str(e)
            )
            return MemoryStats(
                short_term_count=0,
                long_term_count=0,
                total_tokens=0,
                last_pruned=None,
                summary_length=0
            )


# Global memory manager instance
_memory_manager = MemoryManager()


# Backward compatibility functions
def append_to_memory(state: TherapyState, message: BaseMessage, role: str = "user") -> TherapyState:
    """Backward compatibility wrapper."""
    return _memory_manager.append_to_memory(state, message, role)


def get_memory(state: TherapyState, limit: int = 6, from_db: bool = True) -> List[BaseMessage]:
    """Backward compatibility wrapper."""
    return _memory_manager.get_memory(state, limit, from_db)


def save_to_long_term_memory(user_id: str, content: str, metadata: Optional[Dict] = None) -> bool:
    """Backward compatibility wrapper."""
    return _memory_manager.save_to_long_term_memory(user_id, content, metadata)


def search_long_term_memory(user_id: str, query: str, k: int = 3) -> List[Document]:
    """Backward compatibility wrapper."""
    result = _memory_manager.search_long_term_memory(user_id, query, k)
    return result.documents


def prune_messages(state: TherapyState, max_tokens: int = 1200) -> TherapyState:
    """Backward compatibility wrapper."""
    return _memory_manager.prune_messages(state, max_tokens)
