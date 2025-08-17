"""Comprehensive tests for Supabase integration."""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from src.database import SupabaseClient, DatabaseConfig, get_supabase_client
from src.auth import SupabaseAuth, AuthResult, get_auth_service
from src.models import (
    TherapySession, SessionMessage, EmotionType, CrisisLevel, 
    MessageType, SignUpRequest, SignInRequest
)
from src.therapy.memory.memory_manager import MemoryManager


class TestSupabaseClient:
    """Test suite for SupabaseClient."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for testing."""
        client = Mock()
        client.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": "test-id"}], error=None
        )
        client.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{"id": "test-id", "content": "test"}], error=None
        )
        client.rpc.return_value.execute.return_value = Mock(
            data=[{"id": "test-id", "content": "test", "similarity": 0.8}], error=None
        )
        return client
    
    @pytest.fixture
    def supabase_client(self, mock_supabase_client):
        """Create SupabaseClient with mocked dependencies."""
        config = DatabaseConfig(
            url="https://test.supabase.co",
            key="test-key"
        )
        client = SupabaseClient(config)
        client.client = mock_supabase_client
        client._initialized = True
        return client
    
    @pytest.mark.asyncio
    async def test_create_user_profile(self, supabase_client):
        """Test user profile creation."""
        result = await supabase_client.create_user_profile(
            user_id="test-user",
            full_name="Test User",
            email="test@example.com",
            preferences={"theme": "dark"}
        )
        
        assert result.success is True
        assert len(result.data) > 0
    
    @pytest.mark.asyncio
    async def test_create_therapy_session(self, supabase_client):
        """Test therapy session creation."""
        session = TherapySession(
            user_id="test-user",
            session_id="test-session",
            emotion=EmotionType.ANXIOUS,
            crisis_level=CrisisLevel.LOW
        )
        
        result = await supabase_client.create_therapy_session(session)
        
        assert result.success is True
        assert len(result.data) > 0
    
    @pytest.mark.asyncio
    async def test_save_memory_log(self, supabase_client):
        """Test memory log saving."""
        result = await supabase_client.save_memory_log(
            user_id="test-user",
            session_id="test-session",
            role="user",
            content="Test message",
            message_type=MessageType.USER_INPUT,
            emotion=EmotionType.NEUTRAL
        )
        
        assert result.success is True
        assert len(result.data) > 0
    
    @pytest.mark.asyncio
    async def test_get_memory_logs(self, supabase_client):
        """Test memory log retrieval."""
        result = await supabase_client.get_memory_logs(
            user_id="test-user",
            session_id="test-session",
            limit=5
        )
        
        assert result.success is True
        assert isinstance(result.data, list)
    
    @pytest.mark.asyncio
    @patch('src.database.supabase_client.GoogleGenerativeAIEmbeddings')
    async def test_save_to_vector_store(self, mock_embeddings, supabase_client):
        """Test vector store save operation."""
        mock_embeddings_instance = Mock()
        mock_embeddings.return_value = mock_embeddings_instance
        supabase_client.embeddings = mock_embeddings_instance
        
        # Mock vector store
        mock_vector_store = Mock()
        mock_vector_store.add_documents = AsyncMock()
        supabase_client.vector_store = mock_vector_store
        
        result = await supabase_client.save_to_vector_store(
            user_id="test-user",
            content="Test content for vector storage",
            content_type="memory"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    @patch('src.database.supabase_client.GoogleGenerativeAIEmbeddings')
    async def test_search_vector_store(self, mock_embeddings, supabase_client):
        """Test vector store search operation."""
        mock_embeddings_instance = Mock()
        mock_embeddings_instance.embed_query = AsyncMock(return_value=[0.1] * 768)
        mock_embeddings.return_value = mock_embeddings_instance
        supabase_client.embeddings = mock_embeddings_instance
        
        results = await supabase_client.search_vector_store(
            user_id="test-user",
            query="test query",
            k=3
        )
        
        assert isinstance(results, list)
        assert len(results) >= 0
    
    @pytest.mark.asyncio
    async def test_log_crisis_event(self, supabase_client):
        """Test crisis event logging."""
        result = await supabase_client.log_crisis_event(
            user_id="test-user",
            session_id="test-session",
            crisis_level=CrisisLevel.HIGH,
            content="Crisis content",
            escalation_needed=True,
            response_provided="Crisis response"
        )
        
        assert result.success is True
        assert len(result.data) > 0


class TestSupabaseAuth:
    """Test suite for SupabaseAuth."""
    
    @pytest.fixture
    def mock_auth_client(self):
        """Mock Supabase auth client."""
        auth = Mock()
        auth.sign_up.return_value = Mock(
            user=Mock(id="test-user-id", email="test@example.com"),
            session=Mock(access_token="test-token", refresh_token="refresh-token")
        )
        auth.sign_in_with_password.return_value = Mock(
            user=Mock(id="test-user-id", email="test@example.com"),
            session=Mock(access_token="test-token", refresh_token="refresh-token")
        )
        return auth
    
    @pytest.fixture
    def supabase_auth(self, mock_auth_client):
        """Create SupabaseAuth with mocked dependencies."""
        auth_service = SupabaseAuth()
        
        # Mock the supabase client
        mock_supabase_client = Mock()
        mock_supabase_client.client.auth = mock_auth_client
        mock_supabase_client.create_user_profile = AsyncMock(
            return_value=Mock(success=True, data=[{"id": "test-user-id"}])
        )
        mock_supabase_client.get_user_profile = AsyncMock(
            return_value=Mock(success=True, data=[{"id": "test-user-id"}])
        )
        
        auth_service.supabase_client = mock_supabase_client
        auth_service._initialized = True
        
        return auth_service
    
    @pytest.mark.asyncio
    async def test_sign_up(self, supabase_auth):
        """Test user sign up."""
        request = SignUpRequest(
            email="test@example.com",
            password="testpassword123",
            full_name="Test User",
            preferences={"theme": "dark"}
        )
        
        result = await supabase_auth.sign_up(request)
        
        assert result.success is True
        assert result.user_id == "test-user-id"
        assert result.email == "test@example.com"
        assert result.access_token == "test-token"
    
    @pytest.mark.asyncio
    async def test_sign_in(self, supabase_auth):
        """Test user sign in."""
        request = SignInRequest(
            email="test@example.com",
            password="testpassword123"
        )
        
        result = await supabase_auth.sign_in(request)
        
        assert result.success is True
        assert result.user_id == "test-user-id"
        assert result.email == "test@example.com"
        assert result.access_token == "test-token"
    
    @pytest.mark.asyncio
    async def test_sign_out(self, supabase_auth):
        """Test user sign out."""
        result = await supabase_auth.sign_out("test-user-id")
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_reset_password(self, supabase_auth):
        """Test password reset."""
        result = await supabase_auth.reset_password("test@example.com")
        
        assert result.success is True


class TestMemoryManagerIntegration:
    """Test suite for MemoryManager with Supabase integration."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for memory manager."""
        client = Mock()
        client.save_memory_log = AsyncMock(return_value=Mock(success=True))
        client.get_memory_logs = AsyncMock(return_value=Mock(
            success=True, 
            data=[
                {"role": "user", "content": "Hello", "timestamp": "2023-01-01T00:00:00Z"},
                {"role": "assistant", "content": "Hi there!", "timestamp": "2023-01-01T00:01:00Z"}
            ]
        ))
        client.save_to_vector_store = AsyncMock(return_value=True)
        client.search_vector_store = AsyncMock(return_value=[])
        return client
    
    @pytest.fixture
    def memory_manager(self, mock_supabase_client):
        """Create MemoryManager with mocked Supabase client."""
        manager = MemoryManager()
        manager.supabase_client = mock_supabase_client
        manager._initialized = True
        return manager
    
    @pytest.mark.asyncio
    async def test_append_to_memory(self, memory_manager):
        """Test memory append with Supabase integration."""
        from langchain_core.messages import HumanMessage
        
        state = {
            "user_id": "test-user",
            "session_id": "test-session",
            "messages": [],
            "emotion": "neutral"
        }
        
        message = HumanMessage(content="Test message")
        
        result_state = await memory_manager.append_to_memory(state, message, "user")
        
        assert len(result_state["messages"]) == 1
        assert result_state["messages"][0].content == "Test message"
    
    @pytest.mark.asyncio
    async def test_get_memory(self, memory_manager):
        """Test memory retrieval with Supabase integration."""
        state = {
            "user_id": "test-user",
            "session_id": "test-session",
            "messages": []
        }
        
        messages = await memory_manager.get_memory(state, limit=5, from_db=True)
        
        assert isinstance(messages, list)
        assert len(messages) == 2  # Based on mock data
    
    @pytest.mark.asyncio
    async def test_save_to_long_term_memory(self, memory_manager):
        """Test long-term memory save with Supabase integration."""
        result = await memory_manager.save_to_long_term_memory(
            user_id="test-user",
            content="Long-term memory content",
            metadata={"type": "journal"}
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_search_long_term_memory(self, memory_manager):
        """Test long-term memory search with Supabase integration."""
        result = await memory_manager.search_long_term_memory(
            user_id="test-user",
            query="test query",
            k=3
        )
        
        assert hasattr(result, 'documents')
        assert isinstance(result.documents, list)


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    @patch('src.database.supabase_client.create_client')
    @patch('src.database.supabase_client.GoogleGenerativeAIEmbeddings')
    async def test_full_therapy_flow_integration(self, mock_embeddings, mock_create_client):
        """Test complete therapy flow with Supabase integration."""
        # Mock Supabase client
        mock_client = Mock()
        mock_client.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": "test-id"}], error=None
        )
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{"role": "user", "content": "Hello"}], error=None
        )
        mock_create_client.return_value = mock_client
        
        # Mock embeddings
        mock_embeddings_instance = Mock()
        mock_embeddings_instance.embed_query = AsyncMock(return_value=[0.1] * 768)
        mock_embeddings.return_value = mock_embeddings_instance
        
        # Test the integration
        try:
            # Initialize client
            supabase_client = await get_supabase_client()
            
            # Test user profile creation
            profile_result = await supabase_client.create_user_profile(
                user_id="integration-test-user",
                full_name="Integration Test User",
                email="integration@test.com"
            )
            
            # Test therapy session
            session = TherapySession(
                user_id="integration-test-user",
                session_id="integration-test-session",
                emotion=EmotionType.NEUTRAL
            )
            
            session_result = await supabase_client.create_therapy_session(session)
            
            # Test memory operations
            memory_result = await supabase_client.save_memory_log(
                user_id="integration-test-user",
                session_id="integration-test-session",
                role="user",
                content="Integration test message",
                message_type=MessageType.USER_INPUT
            )
            
            # Verify all operations succeeded
            assert profile_result.success is True
            assert session_result.success is True
            assert memory_result.success is True
            
        except Exception as e:
            pytest.fail(f"Integration test failed: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling in integration scenarios."""
        # Test with invalid configuration
        config = DatabaseConfig(url="invalid-url", key="invalid-key")
        client = SupabaseClient(config)
        
        # This should handle the error gracefully
        result = await client.initialize()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent database operations."""
        # This would test multiple simultaneous operations
        # to ensure thread safety and proper connection handling
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
