from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from src.config import get_settings
from src.models import TherapyState, MessageType, EmotionType, CrisisLevel
from src.utils import log_therapy_event, timing_decorator
from src.database import get_supabase_client
from typing import Dict, List, Optional
import datetime
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
        self.supabase_client = None
        self._encoding = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure Supabase client is initialized."""
        if not self._initialized:
            self.supabase_client = await get_supabase_client()
            self._initialized = True
    
    def _get_encoding(self):
        """Get token encoding for text processing."""
        if self._encoding is None:
            try:
                self._encoding = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # Fallback: simple word-based encoding
                self._encoding = type('DummyEncoding', (), {'encode': lambda _, text: text.split()})()
        return self._encoding
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self._get_encoding().encode(text))
    
    @timing_decorator("append_to_memory")
    async def append_to_memory(
        self, 
        state: TherapyState, 
        message: BaseMessage, 
        role: str = "user"
    ) -> TherapyState:
        """Enhanced memory append with monitoring and error handling."""
        await self._ensure_initialized()
        
        user_id = state["user_id"]
        session_id = state.get("session_id", "default")
        
        # Add to state first (always succeeds)
        state["messages"].append(message)
        
        try:
            # Prepare data for database save
            message_type = MessageType.USER if role == "user" else MessageType.ASSISTANT
            emotion = EmotionType(state.get("emotion")) if state.get("emotion") else None
            crisis_level = CrisisLevel(state.get("crisis_level")) if state.get("crisis_level") else None
            
            result = await self.supabase_client.save_memory_log(
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=message.content,
                message_type=message_type,
                emotion=emotion,
                crisis_level=crisis_level,
                metadata=self._extract_metadata(state)
            )
            
            log_therapy_event(
                event="memory_appended",
                user_id=user_id, session_id=session_id, role=role,
                message_length=len(message.content), total_messages=len(state["messages"]),
                db_success=result.success
            )
            
        except Exception as e:
            log_therapy_event(
                event="memory_append_failed",
                user_id=user_id, session_id=session_id, error=str(e)
            )
        
        return state
    
    def _extract_metadata(self, state: TherapyState) -> Dict:
        """Extract relevant metadata from therapy state."""
        return {
            "mode": state.get("mode"),
            "journal_entry": state.get("journal_entry"),
            "attack": state.get("attack")
        }


    @timing_decorator("get_memory")
    async def get_memory(
        self, 
        state: TherapyState, 
        limit: int = 6, 
        from_db: bool = True
    ) -> List[BaseMessage]:
        """Enhanced memory retrieval with monitoring."""
        user_id = state["user_id"]
        session_id = state.get("session_id", "default")
        
        if not from_db:
            messages = state["messages"][-limit:]
            log_therapy_event(
                event="memory_retrieved_from_state",
                user_id=user_id, session_id=session_id, message_count=len(messages)
            )
            return messages

        try:
            await self._ensure_initialized()
            
            result = await self.supabase_client.get_memory_logs(
                user_id=user_id, session_id=session_id, limit=limit
            )
            
            messages = []
            if result.success:
                messages = [
                    HumanMessage(content=row["content"]) if row["role"] == "user" 
                    else AIMessage(content=row["content"])
                    for row in reversed(result.data)
                ]
            
            log_therapy_event(
                event="memory_retrieved_from_db",
                user_id=user_id, session_id=session_id,
                message_count=len(messages), requested_limit=limit, db_success=result.success
            )
            
            return messages
            
        except Exception as e:
            log_therapy_event(
                event="memory_retrieval_failed",
                user_id=user_id, session_id=session_id, error=str(e)
            )
            return state["messages"][-limit:]

    @timing_decorator("save_long_term_memory")
    async def save_to_long_term_memory(
        self, 
        user_id: str, 
        content: str, 
        metadata: Optional[Dict] = None
    ) -> bool:
        """Enhanced long-term memory save with monitoring."""
        await self._ensure_initialized()
        
        try:
            content_type = metadata.get("type", "memory") if metadata else "memory"
            
            success = await self.supabase_client.save_to_vector_store(
                user_id=user_id,
                content=content,
                content_type=content_type,
                metadata=metadata
            )
            
            log_therapy_event(
                event="long_term_memory_saved",
                user_id=user_id, content_length=len(content),
                content_type=content_type, success=success
            )
            
            return success
            
        except Exception as e:
            log_therapy_event(
                event="long_term_memory_save_failed",
                user_id=user_id, error=str(e)
            )
            return False


    @timing_decorator("search_long_term_memory")
    async def search_long_term_memory(
        self, 
        user_id: str, 
        query: str, 
        k: int = 3,
        days_filter: int = 30
    ) -> MemorySearchResult:
        """Enhanced long-term memory search with monitoring."""
        await self._ensure_initialized()
        
        import time
        start_time = time.time()
        
        try:
            threshold = 0.7 if days_filter else 0.5
            
            results = await self.supabase_client.search_vector_store(
                user_id=user_id, query=query, k=k, threshold=threshold
            )
            
            # Filter by date if specified
            if days_filter and results:
                results = self._filter_by_date(results, days_filter)
            
            search_time = (time.time() - start_time) * 1000
            
            log_therapy_event(
                event="long_term_memory_searched",
                user_id=user_id, query_length=len(query), results_found=len(results),
                search_time_ms=search_time, k_requested=k
            )
            
            return MemorySearchResult(
                documents=results, total_found=len(results),
                search_time_ms=search_time, query=query, user_id=user_id
            )
            
        except Exception as e:
            log_therapy_event(
                event="long_term_memory_search_failed",
                user_id=user_id, error=str(e)
            )
            return MemorySearchResult(
                documents=[], total_found=0, search_time_ms=0,
                query=query, user_id=user_id
            )
    
    def _filter_by_date(self, documents: List[Document], days: int) -> List[Document]:
        """Filter documents by date threshold."""
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        filtered_results = []
        
        for doc in documents:
            try:
                doc_date = datetime.datetime.fromisoformat(
                    doc.metadata.get("timestamp", "")
                )
                if doc_date >= cutoff_date:
                    filtered_results.append(doc)
            except Exception:
                # Include docs with invalid timestamps
                filtered_results.append(doc)
        
        return filtered_results

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
        total_tokens = sum(self.count_tokens(msg.content) for msg in messages)
        
        if total_tokens <= max_tokens:
            return state
        
        try:
            # Summarize older half
            cutoff = len(messages) // 2
            to_summarize = messages[:cutoff]
            remaining = messages[cutoff:]
            
            # Create summary (limit to 2000 chars)
            summary_text = "\n".join(m.content for m in to_summarize)[:2000]
            
            # Update state
            existing_summary = state.get("summary", "")
            state["summary"] = (existing_summary + "\n" + summary_text).strip()
            state["messages"] = remaining
            
            log_therapy_event(
                event="memory_pruned",
                user_id=user_id, session_id=session_id,
                original_tokens=total_tokens, original_messages=len(messages),
                remaining_messages=len(remaining), summary_length=len(state["summary"])
            )
            
            return state
            
        except Exception as e:
            log_therapy_event(
                event="memory_pruning_failed",
                user_id=user_id, session_id=session_id, error=str(e)
            )
            return state

    async def get_memory_stats(self, user_id: str) -> MemoryStats:
        """Get memory statistics for monitoring."""
        await self._ensure_initialized()
        
        try:
            # Get short-term memory count
            short_term_result = await self.supabase_client.get_memory_logs(user_id, limit=1000)
            short_term_count = len(short_term_result.data) if short_term_result.success else 0
            
            # Note: Long-term count would require additional DB query
            # For now, return basic stats
            return MemoryStats(
                short_term_count=short_term_count,
                long_term_count=0,  # Would need separate query
                total_tokens=0,     # Would need calculation
                last_pruned=None,   # Would need tracking
                summary_length=0    # Would need calculation
            )
            
        except Exception as e:
            log_therapy_event(
                event="memory_stats_failed",
                user_id=user_id, error=str(e)
            )
            return MemoryStats(
                short_term_count=0, long_term_count=0,
                total_tokens=0, last_pruned=None, summary_length=0
            )


# Global memory manager instance
_memory_manager = MemoryManager()


async def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance."""
    await _memory_manager._ensure_initialized()
    return _memory_manager


# Backward compatibility functions
async def append_to_memory(state: TherapyState, message: BaseMessage, role: str = "user") -> TherapyState:
    """Backward compatibility wrapper."""
    return await _memory_manager.append_to_memory(state, message, role)


async def get_memory(state: TherapyState, limit: int = 6, from_db: bool = True) -> List[BaseMessage]:
    """Backward compatibility wrapper."""
    return await _memory_manager.get_memory(state, limit, from_db)


async def save_to_long_term_memory(user_id: str, content: str, metadata: Optional[Dict] = None) -> bool:
    """Backward compatibility wrapper."""
    return await _memory_manager.save_to_long_term_memory(user_id, content, metadata)


async def search_long_term_memory(user_id: str, query: str, k: int = 3) -> List[Document]:
    """Backward compatibility wrapper."""
    result = await _memory_manager.search_long_term_memory(user_id, query, k)
    return result.documents


def prune_messages(state: TherapyState, max_tokens: int = 1200) -> TherapyState:
    """Backward compatibility wrapper."""
    return _memory_manager.prune_messages(state, max_tokens)
