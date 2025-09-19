"""Simple and efficient Supabase client for AI therapist."""
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import asyncio

from supabase import create_client, Client
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document

from src.config import get_settings
from src.models import TherapySession, CrisisLevel, EmotionType, MessageType
from src.utils import log_event, timing_decorator


class SupabaseClient:
    """Simple and efficient Supabase client for therapy app integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[Client] = None
        self.vector_store: Optional[SupabaseVectorStore] = None
        self.embeddings: Optional[GoogleGenerativeAIEmbeddings] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize Supabase client and vector store."""
        try:
            # Load configuration
            url = os.getenv("SUPABASE_URL") or self.settings.database.supabase_url
            key = os.getenv("SUPABASE_KEY") or self.settings.database.supabase_key
            service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if not url or not key:
                raise ValueError("Supabase URL and key must be configured")
            
            # Initialize client
            effective_key = service_role_key or key
            self.client = create_client(url, effective_key)
            
            # Initialize vector store if Google API key is available
            self._init_vector_store()
            
            self._initialized = True
            log_event(event="supabase_client_initialized", url=url[:50] + "...")
            return True
            
        except Exception as e:
            log_event(event="supabase_initialization_failed", error=str(e))
            return False
    
    def _init_vector_store(self):
        """Initialize vector store components."""
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            return
        
        try:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=google_api_key
            )
            self.vector_store = SupabaseVectorStore(
                client=self.client,
                embedding=self.embeddings,
                table_name="documents",
                query_name="match_documents"
            )
        except Exception as e:
            log_event(event="embeddings_init_warning", error=str(e))
    
    def _ensure_initialized(self):
        """Ensure client is initialized."""
        if not self._initialized:
            raise RuntimeError("SupabaseClient not initialized. Call initialize() first.")
    
    # === User Profile Management ===
    
    @timing_decorator("create_user_profile")
    async def create_user_profile(
        self, 
        user_id: str, 
        full_name: str, 
        email: str,
        preferences: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """Create user profile."""
        self._ensure_initialized()
        
        try:
            data = {
                "id": user_id,
                "full_name": full_name,
                "email": email,
                "preferences": preferences or {}
            }
            
            result = self.client.table("profiles").insert(data).execute()
            if hasattr(result, 'error') and result.error:
                log_event(event="user_profile_creation_failed", user_id=user_id, error=str(result.error))
                return None
            
            log_event(event="user_profile_created", user_id=user_id, email=email)
            return result.data[0] if result.data else None
            
        except Exception as e:
            log_event(event="user_profile_creation_failed", user_id=user_id, error=str(e))
            return None
    
    @timing_decorator("get_user_profile")
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile."""
        self._ensure_initialized()
        
        try:
            result = self.client.table("profiles").select("*").eq("id", user_id).execute()
            if hasattr(result, 'error') and result.error:
                return None
            return result.data[0] if result.data else None
            
        except Exception:
            return None
    
    # === Memory Management ===
    
    @timing_decorator("save_memory_log")
    async def save_memory_log(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        message_type: MessageType = MessageType.USER,
        emotion: Optional[EmotionType] = None,
        crisis_level: Optional[CrisisLevel] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Save memory log entry."""
        self._ensure_initialized()
        
        try:
            data = {
                "user_id": user_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "message_type": message_type.value,
                "emotion": emotion.value if emotion else None,
                "crisis_level": crisis_level.value if crisis_level else None,
                "message_length": len(content),
                "token_count": len(content.split()),  # Simple approximation
                "metadata": metadata or {}
            }
            
            result = self.client.table("memory_logs").insert(data).execute()
            return not (hasattr(result, 'error') and result.error)
            
        except Exception as e:
            log_event(event="memory_log_save_failed", user_id=user_id, session_id=session_id, error=str(e))
            return False

    @timing_decorator("get_memory_logs")
    async def get_memory_logs(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        order: str = "desc",
    ) -> List[Dict[str, Any]]:
        """Get memory logs for a user/session with pagination."""
        self._ensure_initialized()
        
        try:
            query = self.client.table("memory_logs").select("*").eq("user_id", user_id)
            
            if session_id:
                query = query.eq("session_id", session_id)
            
            desc_flag = order.lower() != "asc"
            result = (
                query
                .order("timestamp", desc=desc_flag)
                .range(offset, offset + limit - 1)
                .execute()
            )
            
            if hasattr(result, 'error') and result.error:
                return []
            return result.data or []
            
        except Exception:
            return []
    
    @timing_decorator("get_memory_logs_keyset")
    async def get_memory_logs_keyset(
        self,
        user_id: str,
        session_id: str,
        limit: int = 50,
        order: str = "asc",
        after_created_at: Optional[str] = None,
        before_created_at: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get memory logs using keyset pagination over created_at."""
        self._ensure_initialized()
        
        try:
            q = (
                self.client.table("memory_logs")
                .select("*")
                .eq("user_id", user_id)
                .eq("session_id", session_id)
            )

            desc_flag = order.lower() != "asc"

            # Apply cursor filters
            if after_created_at and not before_created_at:
                q = q.gt("created_at", after_created_at)
            if before_created_at and not after_created_at:
                q = q.lt("created_at", before_created_at)

            # Stable ordering by created_at with tie-breaker id if available
            q = q.order("created_at", desc=desc_flag).order("id", desc=desc_flag).limit(limit)

            result = q.execute()
            if hasattr(result, 'error') and result.error:
                return []
            return result.data or []
            
        except Exception:
            return []
    
    # === Therapy Session Management ===
    
    @timing_decorator("create_therapy_session")
    async def create_therapy_session(self, session: TherapySession) -> bool:
        """Create therapy session record."""
        self._ensure_initialized()
        
        try:
            data = {
                "user_id": session.user_id,
                "session_id": session.id,
                "emotion": session.emotion_detected.value if session.emotion_detected else None,
                "crisis_level": (
                    session.crisis_level.value 
                    if session.crisis_level and session.crisis_level.value != "none" 
                    else None
                ),
                "processing_status": (
                    session.processing_status.value 
                    if getattr(session, "processing_status", None) 
                    else "pending"
                ),
                "session_summary": session.summary,
                "metadata": session.metadata,
            }
            
            result = self.client.table("therapy_sessions").insert(data).execute()
            success = not (hasattr(result, 'error') and result.error)
            
            if success:
                log_event(event="therapy_session_created", user_id=session.user_id, session_id=session.id)
            else:
                log_event(event="therapy_session_creation_failed", user_id=session.user_id, error=str(result.error))
            
            return success
            
        except Exception as e:
            log_event(event="therapy_session_creation_failed", user_id=session.user_id, error=str(e))
            return False
    
    @timing_decorator("update_therapy_session")
    async def update_therapy_session(
        self, 
        user_id: str, 
        session_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """Update therapy session."""
        self._ensure_initialized()
        
        try:
            result = (
                self.client.table("therapy_sessions")
                .update(updates)
                .eq("user_id", user_id)
                .eq("session_id", session_id)
                .execute()
            )
            
            success = not (hasattr(result, 'error') and result.error)
            if success:
                log_event(event="therapy_session_updated", user_id=user_id, session_id=session_id)
            
            return success
            
        except Exception as e:
            log_event(event="therapy_session_update_failed", user_id=user_id, session_id=session_id, error=str(e))
            return False
    
    # === Vector Store Operations ===
    
    @timing_decorator("save_to_vector_store")
    async def save_to_vector_store(
        self,
        user_id: str,
        content: str,
        content_type: str = "memory",
        metadata: Optional[Dict] = None
    ) -> bool:
        """Save content to vector store."""
        self._ensure_initialized()
        
        if not self.vector_store:
            return False
        
        try:
            full_metadata = {
                "user_id": user_id,
                "content_type": content_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if metadata:
                full_metadata.update(metadata)
            
            document = Document(page_content=content, metadata=full_metadata)
            await asyncio.to_thread(self.vector_store.add_documents, [document])
            
            log_event(event="vector_store_save_success", user_id=user_id, content_type=content_type)
            return True
            
        except Exception as e:
            log_event(event="vector_store_save_failed", user_id=user_id, error=str(e))
            return False
    
    @timing_decorator("search_vector_store")
    async def search_vector_store(
        self,
        user_id: str,
        query: str,
        k: int = 3,
        threshold: float = 0.7
    ) -> List[Document]:
        """Search vector store for relevant documents."""
        self._ensure_initialized()
        
        if not self.vector_store or not self.embeddings:
            return []
        
        try:
            embedding = await asyncio.to_thread(self.embeddings.embed_query, query)
            
            # Try enhanced RPC function first
            result = self.client.rpc(
                "match_documents",
                {
                    "user_id_param": user_id,
                    "query_embedding": embedding,
                    "match_threshold": threshold,
                    "match_count": k
                }
            ).execute()
            
            # Fallback to simple RPC if enhanced version fails
            if hasattr(result, 'error') and result.error:
                result = self.client.rpc(
                    "match_documents",
                    {"user_id": user_id, "query_embedding": embedding, "match_count": k}
                ).execute()
            
            if hasattr(result, 'error') and result.error:
                return []
            
            documents = [
                Document(page_content=row["content"], metadata=row["metadata"])
                for row in result.data or []
            ]
            
            log_event(event="vector_search_completed", user_id=user_id, results_found=len(documents))
            return documents
            
        except Exception as e:
            log_event(event="vector_search_failed", user_id=user_id, error=str(e))
            return []
    
    # === Crisis Management ===
    
    @timing_decorator("log_crisis_event")
    async def log_crisis_event(
        self,
        user_id: str,
        session_id: str,
        crisis_level: CrisisLevel,
        content: str,
        escalation_needed: bool = False,
        response_provided: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Log crisis event."""
        self._ensure_initialized()
        
        try:
            data = {
                "user_id": user_id,
                "session_id": session_id,
                "crisis_level": crisis_level.value,
                "content": content,
                "escalation_needed": escalation_needed,
                "response_provided": response_provided,
                "metadata": metadata or {}
            }
            
            result = self.client.table("crisis_events").insert(data).execute()
            success = not (hasattr(result, 'error') and result.error)
            
            if success:
                log_event(
                    event="crisis_event_logged",
                    user_id=user_id, 
                    session_id=session_id, 
                    crisis_level=crisis_level.value,
                    escalation_needed=escalation_needed
                )
            
            return success
            
        except Exception as e:
            log_event(event="crisis_event_logging_failed", user_id=user_id, session_id=session_id, error=str(e))
            return False
    
    # === Security and Performance Logging ===
    
    async def log_security_event(
        self,
        event_type: str,
        severity: str = "medium",
        user_id: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Log security event."""
        self._ensure_initialized()
        
        try:
            data = {
                "user_id": user_id,
                "event_type": event_type,
                "severity": severity,
                "content": content,
                "metadata": metadata or {}
            }
            
            result = self.client.table("security_events").insert(data).execute()
            return not (hasattr(result, 'error') and result.error)
            
        except Exception:
            return False
    
    async def log_performance_metric(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Log performance metric."""
        self._ensure_initialized()
        
        try:
            data = {
                "user_id": user_id,
                "operation": operation,
                "duration_ms": duration_ms,
                "success": success,
                "metadata": metadata or {}
            }
            
            result = self.client.table("performance_metrics").insert(data).execute()
            return not (hasattr(result, 'error') and result.error)
            
        except Exception:
            return False
    
    # === Cleanup and Maintenance ===
    
    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """Clean up old data beyond retention period."""
        self._ensure_initialized()
        
        cutoff_date = (
            datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) 
            - timedelta(days=days)
        )
        
        tables_to_cleanup = ["memory_logs", "security_events", "performance_metrics"]
        cleanup_results = {}
        
        for table in tables_to_cleanup:
            try:
                result = (
                    self.client.table(table)
                    .delete()
                    .lt("created_at", cutoff_date.isoformat())
                    .execute()
                )
                cleanup_results[table] = len(result.data) if result.data else 0
            except Exception as e:
                log_event(event="cleanup_failed", table=table, error=str(e))
                cleanup_results[table] = 0
        
        return cleanup_results
    
    async def close(self):
        """Close client connections."""
        # Supabase handles connection cleanup automatically
        # Just reset our internal state
        self.client = None
        self.vector_store = None
        self.embeddings = None
        self._initialized = False
        log_event(event="supabase_client_closed")
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for monitoring."""
        if not self._initialized or not self.client:
            return {"status": "disconnected"}
        
        return {
            "status": "connected",
            "pooling": "managed_by_supabase",
            "client_type": "supabase-py",
            "vector_store_enabled": self.vector_store is not None,
            "embeddings_enabled": self.embeddings is not None
        }


# Global client instance
_supabase_client: Optional[SupabaseClient] = None


async def get_supabase_client() -> SupabaseClient:
    """Get initialized Supabase client."""
    global _supabase_client
    
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
        await _supabase_client.initialize()
    
    return _supabase_client