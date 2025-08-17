"""Simplified flow handlers for therapy graph nodes."""
from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from src.therapy.memory.memory_manager import append_to_memory, save_to_long_term_memory
from src.config.constants import ResponseMessages, ClassificationResults
from src.models.enums import AttackType


class InputHandler:
    """Handles input validation and moderation."""
    
    @staticmethod
    def check_moderation(state: Dict[str, Any]) -> Dict[str, Any]:
        """Check input for unsafe content or prompt injection."""
        from src.core.guardrails.input_moderation import contains_unsafe_content, detect_prompt_injection
        
        if contains_unsafe_content(state["input"]):
            return {**state, "attack": AttackType.BLOCKED.value}
        if detect_prompt_injection(state["input"]):
            return {**state, "attack": AttackType.INJECTED.value}
        return {**state, "attack": AttackType.SAFE.value}
    
    @staticmethod
    def check_pii(state: Dict[str, Any]) -> Dict[str, Any]:
        """Check for PII in input."""
        from src.core.guardrails.pii_detection import detect_pii
        
        if detect_pii(state["input"]):
            return {**state, "attack": AttackType.PII_FOUND.value}
        return state


class ResponseHandler:
    """Handles response creation and blocking."""
    
    @staticmethod
    def create_blocked_response(state: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Create a blocked response and update memory."""
        ai_message = AIMessage(content=message)
        state = append_to_memory(state, ai_message, role="assistant")
        return {**state, "response": message}
    
    @staticmethod
    def handle_blocked_input(state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle blocked unsafe input."""
        return ResponseHandler.create_blocked_response(
            state, ResponseMessages.UNSAFE_CONTENT_BLOCKED
        )
    
    @staticmethod
    def handle_prompt_injection(state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompt injection attempts."""
        return ResponseHandler.create_blocked_response(
            state, ResponseMessages.PROMPT_INJECTION_BLOCKED
        )
    
    @staticmethod
    def handle_pii(state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle detected PII in input."""
        return ResponseHandler.create_blocked_response(
            state, ResponseMessages.PII_DETECTED
        )
    
    @staticmethod
    def handle_crisis(state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle crisis situations with supportive message."""
        state = append_to_memory(state, HumanMessage(content=state["input"]), role="user")
        ai_message = AIMessage(content=ResponseMessages.CRISIS_SUPPORT)
        state = append_to_memory(state, ai_message, role="assistant")
        return {**state, "response": ResponseMessages.CRISIS_SUPPORT}


class ClassificationHandler:
    """Handles classification tasks."""
    
    @staticmethod
    async def classify_journal_intent(state: Dict[str, Any]) -> Dict[str, Any]:
        """Classify input as journal or chat."""
        from src.core.llm_utils import async_completion
        from src.config.config import get_settings
        from src.config.constants import SystemPrompts
        
        settings = get_settings()
        user_input = state["input"]
        
        response = await async_completion(
            model=settings.model_light,
            messages=[
                {"role": "system", "content": SystemPrompts.JOURNAL_CLASSIFIER},
                {"role": "user", "content": f"Message: {user_input}"},
            ],
            temperature=settings.temperature_classifiers,
        )
        
        result = response["choices"][0]["message"]["content"].strip().lower()
        return {**state, "mode": result}
    
    @staticmethod
    def is_journal_entry(state: Dict[str, Any]) -> bool:
        """Check if input is classified as journal entry."""
        return state.get("mode") == ClassificationResults.JOURNAL


class JournalHandler:
    """Handles journal entry processing."""
    
    @staticmethod
    async def process_journal_entry(state: Dict[str, Any]) -> Dict[str, Any]:
        """Process journal entry and return reflection."""
        from src.therapy.tools.journal_tool import journal_tool
        
        entry = state["input"]
        reflection = await journal_tool(entry)
        
        # Save to long-term memory
        save_to_long_term_memory(
            state["user_id"], 
            content=entry, 
            metadata={"type": "journal"}
        )
        
        # Update conversation memory
        state = append_to_memory(state, HumanMessage(content=entry), role="user")
        state = append_to_memory(state, AIMessage(content=reflection), role="assistant")
        
        return {**state, "response": reflection}


class SafetyHandler:
    """Handles output safety validation."""
    
    @staticmethod
    def validate_response(state: Dict[str, Any]) -> str:
        """Validate AI response for safety."""
        from src.core.guardrails.input_moderation import contains_dangerous_response
        
        response = state.get("response", "")
        return ClassificationResults.UNSAFE if contains_dangerous_response(response) else ClassificationResults.SAFE
    
    @staticmethod
    def handle_unsafe_response(state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unsafe AI response."""
        blocked_message = ResponseMessages.UNSAFE_RESPONSE_BLOCKED
        ai_message = AIMessage(content=blocked_message)
        state = append_to_memory(state, ai_message, role="assistant")
        return {**state, "response": blocked_message}
