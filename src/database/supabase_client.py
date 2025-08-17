"""Enhanced Supabase client with comprehensive integration for AI therapist."""
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timezone
import asyncio
from contextlib import asynccontextmanager

from supabase import create_client, Client
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document

from src.config import get_settings
from src.models import TherapySession, SessionMessage, CrisisLevel, EmotionType, MessageType
from src.utils import log_therapy_event, timing_decorator, ValidationError


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    url: str
    key: str
    service_role_key: Optional[str] = None
    max_connections: int = 10
    timeout: int = 30


@dataclass
class QueryResult:
    """Structured query result."""
    data: List[Dict[str, Any]]
    count: Optional[int] = None
    error: Optional[str] = None
    success: bool = True


class SupabaseClient:
    """Enhanced Supabase client with comprehensive therapy app integration."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.settings = get_settings()
        self.config = config or self._load_config()
        self.client: Optional[Client] = None
        self.vector_store: Optional[SupabaseVectorStore] = None
        self.embeddings: Optional[GoogleGenerativeAIEmbeddings] = None
        self._initialized = False
    
    def _load_config(self) -> DatabaseConfig:
        """Load database configuration from settings and environment."""
        url = os.getenv("SUPABASE_URL") or self.settings.database.supabase_url
        key = os.getenv("SUPABASE_KEY") or self.settings.database.supabase_key
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url or not key:
            raise ValueError("Supabase URL and key must be configured")
        
        return DatabaseConfig(
            url=url,
            key=key,
            service_role_key=service_role_key,
            max_connections=self.settings.database.max_connections,
            timeout=self.settings.database.timeout
        )
    
    async def initialize(self) -> bool:
        """Initialize Supabase client and vector store."""
        try:
            # Initialize Supabase client
            self.client = create_client(self.config.url, self.config.key)
            
            # Initialize embeddings
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY required for embeddings")
            
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=google_api_key
            )
            
            # Initialize vector store
            self.vector_store = SupabaseVectorStore(
                client=self.client,
                embedding=self.embeddings,
                table_name="documents",
                query_name="match_documents"
            )
            
            # Test connection
            await self._test_connection()
            self._initialized = True
            
            log_therapy_event(
                event="supabase_client_initialized",
                metadata={"url": self.config.url[:50] + "..."}
            )
            
            return True
            
        except Exception as e:
            log_therapy_event(
                event="supabase_initialization_failed",
                error=str(e)
            )
            return False
    
    async def _test_connection(self):
        """Test database connection."""
        try:
            result = self.client.table("profiles").select("count", count="exact").limit(1).execute()
            if result.error:
                raise Exception(f"Connection test failed: {result.error}")
        except Exception as e:
            raise Exception(f"Database connection failed: {str(e)}")
    
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
    ) -> QueryResult:
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
            
            if result.error:
                return QueryResult(data=[], error=str(result.error), success=False)
            
            log_therapy_event(
                event="user_profile_created",
                user_id=user_id,
                email=email
            )
            
            return QueryResult(data=result.data)
            
        except Exception as e:
            log_therapy_event(
                event="user_profile_creation_failed",
                user_id=user_id,
                error=str(e)
            )
            return QueryResult(data=[], error=str(e), success=False)
    
    @timing_decorator("get_user_profile")
    async def get_user_profile(self, user_id: str) -> QueryResult:
        """Get user profile."""
        self._ensure_initialized()
        
        try:
            result = self.client.table("profiles").select("*").eq("id", user_id).execute()
            
            if result.error:
                return QueryResult(data=[], error=str(result.error), success=False)
            
            return QueryResult(data=result.data)
            
        except Exception as e:
            return QueryResult(data=[], error=str(e), success=False)
    
    # === Therapy Session Management ===
    
    @timing_decorator("create_therapy_session")
    async def create_therapy_session(self, session: TherapySession) -> QueryResult:
        """Create therapy session record."""
        self._ensure_initialized()
        
        try:
            data = {
                "user_id": session.user_id,
                "session_id": session.session_id,
                "emotion": session.emotion.value if session.emotion else None,
                "emotion_confidence": session.emotion_confidence,
                "crisis_level": session.crisis_level.value if session.crisis_level else None,
                "processing_status": session.processing_status.value if session.processing_status else "pending",
                "session_summary": session.session_summary,
                "metadata": session.metadata or {}
            }
            
            result = self.client.table("therapy_sessions").insert(data).execute()
            
            if result.error:
                return QueryResult(data=[], error=str(result.error), success=False)
            
            log_therapy_event(
                event="therapy_session_created",
                user_id=session.user_id,
                session_id=session.session_id
            )
            
            return QueryResult(data=result.data)
            
        except Exception as e:
            log_therapy_event(
                event="therapy_session_creation_failed",
                user_id=session.user_id,
                error=str(e)
            )
            return QueryResult(data=[], error=str(e), success=False)
    
    @timing_decorator("update_therapy_session")
    async def update_therapy_session(
        self, 
        user_id: str, 
        session_id: str, 
        updates: Dict[str, Any]
    ) -> QueryResult:
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
            
            if result.error:
                return QueryResult(data=[], error=str(result.error), success=False)
            
            log_therapy_event(
                event="therapy_session_updated",
                user_id=user_id,
                session_id=session_id,
                updates=list(updates.keys())
            )
            
            return QueryResult(data=result.data)
            
        except Exception as e:
            log_therapy_event(
                event="therapy_session_update_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return QueryResult(data=[], error=str(e), success=False)
    
    # === Memory Management ===
    
    @timing_decorator("save_memory_log")
    async def save_memory_log(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        message_type: MessageType = MessageType.USER_INPUT,
        emotion: Optional[EmotionType] = None,
        emotion_confidence: Optional[float] = None,
        is_crisis: bool = False,
        crisis_level: Optional[CrisisLevel] = None,
        metadata: Optional[Dict] = None
    ) -> QueryResult:
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
                "emotion_confidence": emotion_confidence,
                "is_crisis": is_crisis,
                "crisis_level": crisis_level.value if crisis_level else None,
                "message_length": len(content),
                "token_count": len(content.split()),  # Simple approximation
                "metadata": metadata or {}
            }
            
            result = self.client.table("memory_logs").insert(data).execute()
            
            if result.error:
                return QueryResult(data=[], error=str(result.error), success=False)
            
            return QueryResult(data=result.data)
            
        except Exception as e:
            log_therapy_event(
                event="memory_log_save_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return QueryResult(data=[], error=str(e), success=False)
    
    @timing_decorator("get_memory_logs")
    async def get_memory_logs(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> QueryResult:
        """Get memory logs for user."""
        self._ensure_initialized()
        
        try:
            query = self.client.table("memory_logs").select("*").eq("user_id", user_id)
            
            if session_id:
                query = query.eq("session_id", session_id)
            
            result = query.order("timestamp", desc=True).limit(limit).execute()
            
            if result.error:
                return QueryResult(data=[], error=str(result.error), success=False)
            
            return QueryResult(data=result.data)
            
        except Exception as e:
            return QueryResult(data=[], error=str(e), success=False)
    
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
        
        try:
            full_metadata = {
                "user_id": user_id,
                "content_type": content_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content_length": len(content),
                **(metadata or {})
            }
            
            document = Document(
                page_content=content,
                metadata=full_metadata
            )
            
            await asyncio.to_thread(self.vector_store.add_documents, [document])
            
            log_therapy_event(
                event="vector_store_save_success",
                user_id=user_id,
                content_type=content_type,
                content_length=len(content)
            )
            
            return True
            
        except Exception as e:
            log_therapy_event(
                event="vector_store_save_failed",
                user_id=user_id,
                error=str(e)
            )
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
        
        try:
            # Use the enhanced RPC function
            embedding = await asyncio.to_thread(self.embeddings.embed_query, query)
            
            result = self.client.rpc(
                "match_documents",
                {
                    "user_id_param": user_id,
                    "query_embedding": embedding,
                    "match_threshold": threshold,
                    "match_count": k
                }
            ).execute()
            
            if result.error:
                log_therapy_event(
                    event="vector_search_failed",
                    user_id=user_id,
                    error=str(result.error)
                )
                return []
            
            documents = []
            for row in result.data:
                doc = Document(
                    page_content=row["content"],
                    metadata=row["metadata"]
                )
                documents.append(doc)
            
            log_therapy_event(
                event="vector_search_completed",
                user_id=user_id,
                query_length=len(query),
                results_found=len(documents)
            )
            
            return documents
            
        except Exception as e:
            log_therapy_event(
                event="vector_search_failed",
                user_id=user_id,
                error=str(e)
            )
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
    ) -> QueryResult:
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
            
            if result.error:
                return QueryResult(data=[], error=str(result.error), success=False)
            
            log_therapy_event(
                event="crisis_event_logged",
                user_id=user_id,
                session_id=session_id,
                crisis_level=crisis_level.value,
                escalation_needed=escalation_needed
            )
            
            return QueryResult(data=result.data)
            
        except Exception as e:
            log_therapy_event(
                event="crisis_event_logging_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return QueryResult(data=[], error=str(e), success=False)
    
    # === Security and Performance Logging ===
    
    @timing_decorator("log_security_event")
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
            return not result.error
            
        except Exception:
            return False
    
    @timing_decorator("log_performance_metric")
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
            return not result.error
            
        except Exception:
            return False
    
    # === Cleanup and Maintenance ===
    
    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """Clean up old data beyond retention period."""
        self._ensure_initialized()
        
        cleanup_results = {}
        cutoff_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=days)
        
        tables_to_cleanup = [
            "memory_logs",
            "security_events", 
            "performance_metrics"
        ]
        
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
                log_therapy_event(
                    event="cleanup_failed",
                    table=table,
                    error=str(e)
                )
                cleanup_results[table] = 0
        
        return cleanup_results
    
    async def close(self):
        """Close client connections."""
        if self.client:
            # Supabase client doesn't have explicit close method
            self.client = None
        self._initialized = False


# Global client instance
_supabase_client: Optional[SupabaseClient] = None


async def get_supabase_client() -> SupabaseClient:
    """Get initialized Supabase client."""
    global _supabase_client
    
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
        await _supabase_client.initialize()
    
    return _supabase_client


@asynccontextmanager
async def supabase_session():
    """Context manager for Supabase operations."""
    client = await get_supabase_client()
    try:
        yield client
    finally:
        # Cleanup if needed
        pass
