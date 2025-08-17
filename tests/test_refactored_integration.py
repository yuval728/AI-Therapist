"""Integration tests for refactored AI therapist modules."""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Import refactored modules
from src.models import (
    TherapySession, SessionMessage, EmotionType, CrisisLevel, 
    MessageType, ProcessingStatus
)
from src.utils import (
    log_therapy_event, timing_decorator, validate_user_input,
    ValidationError
)
from src.config import get_settings
from src.core import (
    moderate_input, detect_pii, chat_completion, classify_text
)
from src.therapy import (
    TherapyService, TherapyContext, get_therapy_service,
    InputHandler, ResponseHandler, ClassificationHandler,
    JournalHandler, SafetyHandler, build_therapy_graph
)


class TestRefactoredIntegration:
    """Test suite for validating refactored module integration."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock()
        settings.models.chat_model = "gpt-3.5-turbo"
        settings.models.temperature_chat = 0.7
        settings.models.max_tokens_chat = 1000
        settings.security.enable_input_moderation = True
        settings.security.enable_pii_detection = True
        settings.security.enable_crisis_detection = True
        return settings
    
    @pytest.fixture
    def sample_therapy_state(self):
        """Sample therapy state for testing."""
        return {
            "user_id": "test_user_123",
            "session_id": "session_456",
            "input": "I'm feeling anxious about my presentation tomorrow.",
            "messages": [],
            "emotion": None,
            "is_crisis": False,
            "mode": None
        }
    
    def test_models_integration(self):
        """Test that all models work together properly."""
        # Test TherapySession creation
        session = TherapySession(
            user_id="test_user",
            session_id="test_session",
            emotion=EmotionType.ANXIOUS,
            crisis_level=CrisisLevel.LOW,
            processing_status=ProcessingStatus.IN_PROGRESS
        )
        
        assert session.user_id == "test_user"
        assert session.emotion == EmotionType.ANXIOUS
        assert session.crisis_level == CrisisLevel.LOW
        
        # Test SessionMessage creation
        message = SessionMessage(
            content="Test message",
            message_type=MessageType.USER_INPUT,
            emotion=EmotionType.NEUTRAL
        )
        
        assert message.content == "Test message"
        assert message.message_type == MessageType.USER_INPUT
        assert len(message.content) > 0
    
    def test_utils_integration(self):
        """Test utils module integration."""
        # Test validation
        try:
            validate_user_input("Valid input text", max_length=100)
        except ValidationError:
            pytest.fail("Valid input should not raise ValidationError")
        
        # Test invalid input
        with pytest.raises(ValidationError):
            validate_user_input("", max_length=100)  # Empty input
        
        # Test timing decorator
        @timing_decorator("test_function")
        def test_func():
            return "success"
        
        result = test_func()
        assert result == "success"
    
    @patch('src.config.get_settings')
    def test_config_integration(self, mock_get_settings):
        """Test config module integration."""
        mock_settings = Mock()
        mock_settings.models.chat_model = "test-model"
        mock_get_settings.return_value = mock_settings
        
        settings = get_settings()
        assert settings.models.chat_model == "test-model"
    
    @patch('src.core.moderate_input')
    @patch('src.core.detect_pii')
    def test_core_integration(self, mock_detect_pii, mock_moderate_input):
        """Test core module integration."""
        # Mock responses
        mock_moderate_input.return_value = Mock(
            is_safe=True,
            confidence=0.9,
            detected_issues=[]
        )
        
        mock_detect_pii.return_value = Mock(
            has_pii=False,
            confidence=0.8,
            detected_types=[]
        )
        
        # Test input moderation
        moderation_result = moderate_input("Safe input text", "test_user")
        assert moderation_result.is_safe is True
        assert moderation_result.confidence == 0.9
        
        # Test PII detection
        pii_result = detect_pii("No PII here", "test_user")
        assert pii_result.has_pii is False
        assert pii_result.confidence == 0.8
    
    @patch('src.therapy.services.therapy_service.chat_completion')
    @patch('src.therapy.services.therapy_service.classify_text')
    async def test_therapy_service_integration(self, mock_classify, mock_chat):
        """Test therapy service integration."""
        # Mock responses
        mock_chat.return_value = "I understand you're feeling anxious. Let's talk about it."
        mock_classify.return_value = "anxious"
        
        therapy_service = get_therapy_service()
        
        # Test emotion analysis
        emotion, confidence = await therapy_service.analyze_emotion(
            "I'm feeling anxious", "test_user"
        )
        assert emotion == EmotionType.ANXIOUS
        assert confidence > 0
        
        # Test crisis detection
        is_crisis, crisis_level = await therapy_service.detect_crisis(
            "I'm feeling sad", "test_user"
        )
        assert is_crisis is False
        assert crisis_level is None
    
    @patch('src.therapy.flow_handlers.moderate_input')
    @patch('src.therapy.flow_handlers.detect_pii')
    def test_flow_handlers_integration(self, mock_detect_pii, mock_moderate_input, sample_therapy_state):
        """Test flow handlers integration."""
        # Mock safe input
        mock_moderate_input.return_value = Mock(
            is_safe=True,
            attack_type=None,
            confidence=0.9
        )
        
        mock_detect_pii.return_value = Mock(
            has_pii=False,
            detected_types=[],
            confidence=0.8
        )
        
        # Test input handler
        result = InputHandler.check_moderation(sample_therapy_state)
        assert result["attack"] == "safe"
        
        # Test PII handler
        result = InputHandler.check_pii(sample_therapy_state)
        assert result.get("attack") != "pii_found"
        
        # Test response handler
        blocked_result = ResponseHandler.handle_blocked_input(sample_therapy_state)
        assert "response" in blocked_result
        assert len(blocked_result["response"]) > 0
    
    @patch('src.therapy.flow_handlers.classify_text')
    async def test_classification_handler_integration(self, mock_classify, sample_therapy_state):
        """Test classification handler integration."""
        mock_classify.return_value = "chat"
        
        result = await ClassificationHandler.classify_journal_intent(sample_therapy_state)
        assert result["mode"] == "chat"
        
        is_journal = ClassificationHandler.is_journal_entry({"mode": "journal"})
        assert is_journal is True
        
        is_not_journal = ClassificationHandler.is_journal_entry({"mode": "chat"})
        assert is_not_journal is False
    
    @patch('src.therapy.flow_handlers.journal_tool')
    @patch('src.therapy.flow_handlers.save_to_long_term_memory')
    @patch('src.therapy.flow_handlers.append_to_memory')
    async def test_journal_handler_integration(self, mock_append, mock_save, mock_journal_tool, sample_therapy_state):
        """Test journal handler integration."""
        mock_journal_tool.return_value = "Thank you for sharing your thoughts."
        mock_append.return_value = sample_therapy_state
        mock_save.return_value = True
        
        sample_therapy_state["input"] = "Today I felt anxious about work."
        
        result = await JournalHandler.process_journal_entry(sample_therapy_state)
        assert "response" in result
        assert len(result["response"]) > 0
        
        # Verify journal tool was called
        mock_journal_tool.assert_called_once()
        mock_save.assert_called_once()
    
    @patch('src.therapy.flow_handlers.moderate_output')
    def test_safety_handler_integration(self, mock_moderate_output, sample_therapy_state):
        """Test safety handler integration."""
        # Mock safe response
        mock_moderate_output.return_value = Mock(
            is_safe=True,
            confidence=0.9
        )
        
        sample_therapy_state["response"] = "This is a safe response."
        
        result = SafetyHandler.validate_response(sample_therapy_state)
        assert result == "safe"
        
        # Test unsafe response handling
        unsafe_result = SafetyHandler.handle_unsafe_response(sample_therapy_state)
        assert "response" in unsafe_result
        assert "cannot provide that response" in unsafe_result["response"].lower()
    
    @patch('src.therapy.memory.memory_manager.MemoryManager')
    def test_memory_integration(self, mock_memory_manager):
        """Test memory management integration."""
        # Mock memory manager
        mock_manager = Mock()
        mock_memory_manager.return_value = mock_manager
        
        # Mock memory operations
        mock_manager.append_to_memory.return_value = {"messages": ["test"]}
        mock_manager.get_memory.return_value = []
        mock_manager.save_to_long_term_memory.return_value = True
        mock_manager.search_long_term_memory.return_value = Mock(documents=[])
        
        from src.therapy.memory.memory_manager import (
            append_to_memory, get_memory, save_to_long_term_memory, search_long_term_memory
        )
        
        # Test backward compatibility functions
        state = {"messages": []}
        result = append_to_memory(state, Mock(content="test"), "user")
        assert "messages" in result
        
        memories = get_memory(state)
        assert isinstance(memories, list)
        
        saved = save_to_long_term_memory("user", "content")
        assert saved is True
        
        search_result = search_long_term_memory("user", "query")
        assert hasattr(search_result, 'documents') or isinstance(search_result, list)
    
    @patch('src.therapy.graphs.therapy_flow.get_therapy_service')
    @patch('src.therapy.graphs.therapy_flow.search_long_term_memory')
    @patch('src.therapy.graphs.therapy_flow.get_memory')
    @patch('src.therapy.graphs.therapy_flow.append_to_memory')
    async def test_therapy_flow_integration(self, mock_append, mock_get_memory, mock_search, mock_get_service):
        """Test therapy flow graph integration."""
        # Mock dependencies
        mock_service = Mock()
        mock_service.process_therapy_input = AsyncMock(return_value={
            "response": "I understand how you're feeling.",
            "emotion": "anxious",
            "emotion_confidence": 0.8,
            "is_crisis": False,
            "crisis_level": None
        })
        mock_service.analyze_emotion = AsyncMock(return_value=(EmotionType.ANXIOUS, 0.8))
        mock_service.detect_crisis = AsyncMock(return_value=(False, None))
        
        mock_get_service.return_value = mock_service
        mock_search.return_value = []
        mock_get_memory.return_value = []
        mock_append.return_value = {"messages": []}
        
        # Test graph building
        graph = build_therapy_graph()
        assert graph is not None
        
        # Test that graph has expected structure
        assert hasattr(graph, 'invoke')
    
    def test_end_to_end_integration(self):
        """Test complete end-to-end integration."""
        # This would be a comprehensive test that runs through
        # the entire therapy flow with mocked external dependencies
        
        # For now, just verify that all major components can be imported
        # and instantiated without errors
        
        try:
            # Test model creation
            session = TherapySession(
                user_id="test",
                session_id="test",
                emotion=EmotionType.NEUTRAL
            )
            
            # Test service creation
            therapy_service = get_therapy_service()
            
            # Test graph creation
            graph = build_therapy_graph()
            
            # If we get here, basic integration is working
            assert session is not None
            assert therapy_service is not None
            assert graph is not None
            
        except Exception as e:
            pytest.fail(f"End-to-end integration failed: {str(e)}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
