"""Enhanced flow handlers with improved error handling and monitoring."""
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage
from src.therapy.memory.memory_manager import (
    get_memory_manager,
    append_to_memory,
    save_to_long_term_memory,
)
from src.config.constants import ResponseMessages, ClassificationResults, SystemPrompts
from src.models import AttackType, EmotionType, CrisisLevel, MessageType, ClassificationFormat
from src.core import moderate_input, moderate_output, detect_pii_enhanced, chat_completion, classify_text
from src.utils import log_therapy_event, timing_decorator
import json


class InputHandler:
    """Enhanced input validation and moderation with detailed logging."""
    
    @staticmethod
    @timing_decorator("input_moderation_check")
    def check_moderation(state: Dict[str, Any]) -> Dict[str, Any]:
        """Check input for unsafe content or prompt injection with enhanced monitoring."""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        input_text = state["input"]
        
        try:
            # Use enhanced moderation
            moderation_result = moderate_input(input_text, user_id)
            
            # Log moderation event
            log_therapy_event(
                event="input_moderation_completed",
                user_id=user_id,
                session_id=session_id,
                attack_type=moderation_result.attack_type.value,
                confidence=moderation_result.confidence,
                is_safe=moderation_result.is_safe
            )            
            return {**state, "attack": moderation_result.attack_type.value}
        except Exception as e:
            log_therapy_event(
                event="input_moderation_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            # Default to safe if moderation fails
            return {**state, "attack": AttackType.SAFE.value}
    
    @staticmethod
    @timing_decorator("pii_detection_check")
    def check_pii(state: Dict[str, Any]) -> Dict[str, Any]:
        """Check for PII in input with enhanced detection."""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        input_text = state["input"]
        
        try:
            # Use enhanced PII detection
            pii_result = detect_pii_enhanced(input_text, user_id)
            
            # Log PII detection event
            log_therapy_event(
                event="pii_detection_completed",
                user_id=user_id,
                session_id=session_id,
                has_pii=pii_result.has_pii,
                pii_types=pii_result.pii_types,
                confidence=pii_result.confidence
            )
            
            if pii_result.has_pii:
                return {**state, "attack": AttackType.PII_FOUND.value}
            return state
            
        except Exception as e:
            log_therapy_event(
                event="pii_detection_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return state


class ResponseHandler:
    """Enhanced response creation and blocking with monitoring."""
    
    @staticmethod
    @timing_decorator("create_blocked_response")
    async def create_blocked_response(
        state: Dict[str, Any], 
        message: str, 
        response_type: str = "blocked"
    ) -> Dict[str, Any]:
        """Create a blocked response and update memory with logging."""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        
        try:
            ai_message = AIMessage(content=message)
            try:
                memory_manager = await get_memory_manager()
                state = await memory_manager.append_to_memory(state, ai_message, role="assistant")
            except Exception:
                pass  # Continue without memory if it fails
            
            # Log blocked response
            log_therapy_event(
                event="blocked_response_created",
                user_id=user_id,
                session_id=session_id,
                response_type=response_type,
                message_length=len(message)
            )
            
            return {**state, "response": message}
            
        except Exception as e:
            log_therapy_event(
                event="blocked_response_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            # Fallback response
            return {**state, "response": "I'm unable to process your request at this time."}
    
    @staticmethod
    def handle_blocked_input(state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle blocked unsafe input with enhanced logging."""
        return ResponseHandler.create_blocked_response(
            state, 
            ResponseMessages.UNSAFE_CONTENT_BLOCKED,
            "unsafe_content"
        )
    
    @staticmethod
    def handle_prompt_injection(state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompt injection attempts with enhanced logging."""
        return ResponseHandler.create_blocked_response(
            state, 
            ResponseMessages.PROMPT_INJECTION_BLOCKED,
            "prompt_injection"
        )
    
    @staticmethod
    def handle_pii(state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle detected PII in input with enhanced logging."""
        return ResponseHandler.create_blocked_response(
            state, 
            ResponseMessages.PII_DETECTED,
            "pii_detected"
        )
    
    @staticmethod
    @timing_decorator("crisis_response")
    def handle_crisis(state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle crisis situations with supportive message and escalation."""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        
        try:
            # Add user message to memory
            state = append_to_memory(state, HumanMessage(content=state["input"]), role="user")
            
            # Create crisis response
            ai_message = AIMessage(content=ResponseMessages.CRISIS_SUPPORT)
            state = append_to_memory(state, ai_message, role="assistant")
            
            # Log crisis event with high priority
            log_therapy_event(
                event="crisis_response_provided",
                user_id=user_id,
                session_id=session_id,
                crisis_detected=True,
                escalation_needed=True
            )
            
            return {**state, "response": ResponseMessages.CRISIS_SUPPORT}
            
        except Exception as e:
            log_therapy_event(
                event="crisis_response_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            # Fallback crisis response
            fallback_message = "I'm here to support you. Please reach out to a mental health professional if you need immediate help."
            return {**state, "response": fallback_message}


class ClassificationHandler:
    """Enhanced classification tasks with monitoring and error handling."""
    
    @staticmethod
    @timing_decorator("classification")
    async def classify_intent(state: Dict[str, Any]) -> Dict[str, Any]:
        """Classify input as journal or chat with enhanced monitoring."""
        
        
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        user_input = state["input"]
        
        try:
            # Use enhanced classification
            result = await classify_text(
                text=user_input,
                system_prompt=SystemPrompts.CLASSIFIER,
                user_id=user_id,
                response_format=ClassificationFormat
            )
            log_therapy_event(
                event="classification_completed",
                user_id=user_id,
                session_id=session_id,
                classification_result=result
            )
            result = json.loads(result)
            
            try:
                mode = ClassificationResults.CHAT if result['mode'] == 'chat' else ClassificationResults.JOURNAL
                crisis_level = CrisisLevel(result['crisis_level']) if result['crisis_level'] != 'none' else None
                emotion = EmotionType(result['emotion']) if result['emotion'] != 'neutral' else None
            except Exception as e:
                log_therapy_event(
                    event=f"classification_failed_values{result}",
                    user_id=user_id,
                    session_id=session_id,
                    error=str(e)
                )
                mode = ClassificationResults.CHAT
                crisis_level = "none"
                emotion = "neutral"
            
            # Log classification event
            log_therapy_event(
                event="classification_completed",
                user_id=user_id,
                session_id=session_id,
                mode=mode,
                crisis_level=crisis_level,
                emotion=emotion,
                input_length=len(user_input)
            )
            
            return {**state, "mode": mode, "crisis_level": crisis_level, "emotion": emotion}
            
        except Exception as e:
            log_therapy_event(
                event="classification_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            return {**state, "mode": ClassificationResults.CHAT, "crisis_level": "none", "emotion": "neutral"}
    
    @staticmethod
    def is_journal_entry(state: Dict[str, Any]) -> bool:
        """Check if input is classified as journal entry."""
        return state.get("mode") == ClassificationResults.JOURNAL


class JournalHandler:
    """Enhanced journal entry processing with monitoring."""
    
    @staticmethod
    @timing_decorator("journal_processing")
    async def process_journal_entry(state: Dict[str, Any]) -> Dict[str, Any]:
        """Process journal entry and return reflection with enhanced monitoring."""
        from src.therapy.tools import journal_tool
        
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        entry = state["input"]
        
        try:
            # Process journal entry
            reflection = await journal_tool(entry)
            
            # Save to long-term memory with enhanced metadata
            await save_to_long_term_memory(
                user_id, 
                content=entry, 
                metadata={
                    "type": "journal",
                    "session_id": session_id,
                    "word_count": len(entry.split()),
                }
            )
            
            # Update conversation memory
            state = await append_to_memory(state, HumanMessage(content=entry), role="user")
            state = await append_to_memory(state, AIMessage(content=reflection), role="assistant")
            
            # Log journal processing event
            log_therapy_event(
                event="journal_entry_processed",
                user_id=user_id,
                session_id=session_id,
                entry_length=len(entry),
                reflection_length=len(reflection),
                word_count=len(entry.split())
            )
            
            return {**state, "response": reflection}
            
        except Exception as e:
            log_therapy_event(
                event="journal_processing_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            # Fallback response for journal processing failure
            fallback_response = "Thank you for sharing your thoughts. I appreciate you taking the time to reflect."
            return {**state, "response": fallback_response}


class SafetyHandler:
    """Enhanced output safety validation with monitoring."""
    
    @staticmethod
    @timing_decorator("response_validation")
    def validate_response(state: Dict[str, Any]) -> str:
        """Validate AI response for safety with enhanced monitoring."""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        response = state.get("response", "")
        
        try:
            # Use enhanced output moderation
            moderation_result = moderate_output(response, user_id)
            
            # Log validation event
            log_therapy_event(
                event="response_validation_completed",
                user_id=user_id,
                session_id=session_id,
                is_safe=moderation_result.is_safe,
                confidence=moderation_result.confidence,
                response_length=len(response)
            )
            
            return ClassificationResults.SAFE if moderation_result.is_safe else ClassificationResults.UNSAFE
            
        except Exception as e:
            log_therapy_event(
                event="response_validation_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            # Default to safe if validation fails
            return ClassificationResults.SAFE
    
    @staticmethod
    @timing_decorator("unsafe_response_handling")
    def handle_unsafe_response(state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unsafe AI response with enhanced monitoring."""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        
        try:
            blocked_message = ResponseMessages.UNSAFE_RESPONSE_BLOCKED
            ai_message = AIMessage(content=blocked_message)
            state = append_to_memory(state, ai_message, role="assistant")
            
            # Log unsafe response handling
            log_therapy_event(
                event="unsafe_response_blocked",
                user_id=user_id,
                session_id=session_id,
                original_response=state.get("response", ""),
                blocked_message=blocked_message
            )
            
            return {**state, "response": blocked_message}
            
        except Exception as e:
            log_therapy_event(
                event="unsafe_response_handling_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            # Fallback safe response
            return {**state, "response": "I apologize, but I cannot provide that response."}
