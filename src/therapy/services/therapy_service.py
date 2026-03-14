"""Enhanced therapy service with improved flow management and monitoring."""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from src.models import EmotionType, CrisisLevel
from src.therapy.llm_utils import chat_completion
from src.utils import log_therapy_event, timing_decorator
from src.config import get_settings
from src.config.constants import SystemPrompts, Limits


@dataclass
class TherapyContext:
    """Structured therapy context for better state management."""
    user_id: str
    session_id: str
    input_text: str
    emotion: Optional[EmotionType] = None
    crisis_level: Optional[CrisisLevel] = None
    relevant_memories: List[str] = None
    session_summary: Optional[str] = None
    
    def __post_init__(self):
        if self.relevant_memories is None:
            self.relevant_memories = []


class TherapyService:
    """Enhanced therapy service with comprehensive monitoring and error handling."""
    
    def __init__(self):
        self.settings = get_settings()
        # Prefer a lighter model for classifiers if configured
        self.classifier_model = getattr(self.settings.models, "classifier_model", None) or self.settings.models.chat_model
    
    @timing_decorator("therapy_response_generation")
    async def generate_therapy_response(
        self, 
        context: TherapyContext,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """Generate therapy response with enhanced context and monitoring."""
        try:
            # Build comprehensive prompt
            prompt = self._build_therapy_prompt(context, conversation_history)
            
            # Generate response using enhanced LLM client
            response = await chat_completion(
                messages=prompt,
                model=self.settings.models.chat_model,
                temperature=self.settings.models.temperature_chat,
                max_tokens=self.settings.models.max_tokens_chat,
                user_id=context.user_id
            )
            
            # Log successful response generation
            log_therapy_event(
                event="therapy_response_generated",
                user_id=context.user_id,
                session_id=context.session_id,
                response_length=len(response),
                emotion=context.emotion if context.emotion else None,
                crisis_level=context.crisis_level if context.crisis_level else None,
                memory_count=len(context.relevant_memories)
            )
            
            return response
            
        except Exception as e:
            log_therapy_event(
                event="therapy_response_generation_failed",
                user_id=context.user_id,
                session_id=context.session_id,
                error=str(e)
            )
            # Fallback response
            return "I'm here to support you. Could you tell me more about what's on your mind?"
    
    def _build_therapy_prompt(
        self, 
        context: TherapyContext, 
        history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Build comprehensive therapy prompt with context."""
        system_parts = [
            SystemPrompts.THERAPIST_BASE,
            SystemPrompts.PROVIDE_SUPPORT,
        ]
        
        # Add emotion context if available
        if context.emotion:
            emotion_context = f"User's current emotional state: {context.emotion}"
            system_parts.append(emotion_context)
        
        # Add crisis context if detected
        if context.crisis_level:
            crisis_context = f"Crisis level detected: {context.crisis_level}. Provide extra support and consider escalation if needed."
            system_parts.append(crisis_context)
        
        # Add session summary if available
        if context.session_summary:
            summary_text = context.session_summary[:Limits.SUMMARY_MAX_LENGTH]
            system_parts.append(f"Earlier conversation summary:\n{summary_text}")
        
        # Add relevant memories
        if context.relevant_memories:
            system_parts.append("Relevant past context:")
            for memory in context.relevant_memories[:Limits.RELEVANT_MEMORIES_LIMIT]:
                memory_text = memory[:Limits.MEMORY_CONTENT_MAX_LENGTH]
                system_parts.append(f"- {memory_text}")
        
        # Build message list
        messages = [{"role": "system", "content": "\n\n".join(system_parts)}]
        
        # Add conversation history
        messages.extend(history)
        
        # Add current user input
        messages.append({"role": "user", "content": context.input_text})
        
        return messages
    
    
    async def process_therapy_input(
        self,
        user_id: str,
        session_id: str,
        input_text: str,
        emotion: EmotionType,
        crisis_level: CrisisLevel,
        conversation_history: List[Dict[str, str]],
        relevant_memories: List[str] = None,
        session_summary: str = None
    ) -> Dict[str, Any]:
        """Process therapy input with comprehensive analysis and response generation."""
        try:
            context = TherapyContext(
                user_id=user_id,
                session_id=session_id,
                input_text=input_text,
                emotion=emotion,
                crisis_level=crisis_level,
                relevant_memories=relevant_memories or [],
                session_summary=session_summary
            )
            
            # Generate response
            response = await self.generate_therapy_response(context, conversation_history)
            
            # Return comprehensive result
            return {
                "response": response,
                "emotion": emotion if emotion else None,
                "crisis_level": crisis_level if crisis_level else None,
                "context": context
            }
            
        except Exception as e:
            log_therapy_event(
                event="therapy_input_processing_failed",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )
            # Return fallback response
            return {
                "response": "I'm here to support you. Could you tell me more about what's on your mind?",
                "emotion": None,
                "crisis_level": None,
                "context": None
            }


# Global therapy service instance
_therapy_service = TherapyService()


def get_therapy_service() -> TherapyService:
    """Get the global therapy service instance."""
    return _therapy_service
