"""Enhanced therapy service with improved flow management and monitoring."""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from src.models import TherapySession, SessionMessage, EmotionType, CrisisLevel
from src.core import chat_completion, classify_text
from src.utils import log_therapy_event, timing_decorator, ValidationError
from src.config import get_settings
from src.config.constants import SystemPrompts, Limits


@dataclass
class TherapyContext:
    """Structured therapy context for better state management."""
    user_id: str
    session_id: str
    input_text: str
    emotion: Optional[EmotionType] = None
    emotion_confidence: Optional[float] = None
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
                emotion=context.emotion.value if context.emotion else None,
                crisis_level=context.crisis_level.value if context.crisis_level else None,
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
            emotion_context = f"User's current emotional state: {context.emotion.value}"
            if context.emotion_confidence:
                emotion_context += f" (confidence: {context.emotion_confidence:.2f})"
            system_parts.append(emotion_context)
        
        # Add crisis context if detected
        if context.crisis_level:
            crisis_context = f"Crisis level detected: {context.crisis_level.value}. Provide extra support and consider escalation if needed."
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
    
    @timing_decorator("emotion_analysis")
    async def analyze_emotion(self, text: str, user_id: str) -> tuple[Optional[EmotionType], float]:
        """Analyze emotion from text with confidence scoring."""
        try:
            emotion_prompt = (
                "Analyze the emotional tone of the following text. "
                "Respond with only the primary emotion: happy, sad, angry, anxious, "
                "fearful, surprised, disgusted, neutral, confused, excited, calm, "
                "frustrated, hopeful, lonely, or overwhelmed."
            )
            
            result = await classify_text(
                text=text,
                system_prompt=emotion_prompt,
                user_id=user_id
            )
            
            emotion_str = result.strip().lower()
            
            # Map to EmotionType enum
            emotion_mapping = {
                "happy": EmotionType.HAPPY,
                "sad": EmotionType.SAD,
                "angry": EmotionType.ANGRY,
                "anxious": EmotionType.ANXIOUS,
                "fearful": EmotionType.FEARFUL,
                "surprised": EmotionType.SURPRISED,
                "disgusted": EmotionType.DISGUSTED,
                "neutral": EmotionType.NEUTRAL,
                "confused": EmotionType.CONFUSED,
                "excited": EmotionType.EXCITED,
                "calm": EmotionType.CALM,
                "frustrated": EmotionType.FRUSTRATED,
                "hopeful": EmotionType.HOPEFUL,
                "lonely": EmotionType.LONELY,
                "overwhelmed": EmotionType.OVERWHELMED
            }
            
            emotion = emotion_mapping.get(emotion_str, EmotionType.NEUTRAL)
            confidence = 0.8  # Default confidence, could be enhanced with actual confidence scoring
            
            return emotion, confidence
            
        except Exception as e:
            log_therapy_event(
                event="emotion_analysis_failed",
                user_id=user_id,
                error=str(e)
            )
            return None, 0.0
    
    @timing_decorator("crisis_detection")
    async def detect_crisis(self, text: str, user_id: str) -> tuple[bool, Optional[CrisisLevel]]:
        """Detect crisis situations with severity levels."""
        try:
            crisis_prompt = (
                "Analyze the following text for signs of mental health crisis or self-harm. "
                "Respond with only: 'none', 'low', 'moderate', 'high', or 'critical' "
                "based on the severity of crisis indicators."
            )
            
            result = await classify_text(
                text=text,
                system_prompt=crisis_prompt,
                user_id=user_id
            )
            
            level_str = result.strip().lower()
            
            # Map to CrisisLevel enum
            level_mapping = {
                "none": None,
                "low": CrisisLevel.LOW,
                "moderate": CrisisLevel.MODERATE,
                "high": CrisisLevel.HIGH,
                "critical": CrisisLevel.CRITICAL
            }
            
            crisis_level = level_mapping.get(level_str)
            is_crisis = crisis_level is not None
            
            return is_crisis, crisis_level
            
        except Exception as e:
            log_therapy_event(
                event="crisis_detection_failed",
                user_id=user_id,
                error=str(e)
            )
            return False, None
    
    async def process_therapy_input(
        self,
        user_id: str,
        session_id: str,
        input_text: str,
        conversation_history: List[Dict[str, str]],
        relevant_memories: List[str] = None,
        session_summary: str = None
    ) -> Dict[str, Any]:
        """Process therapy input with comprehensive analysis and response generation."""
        try:
            # Analyze emotion
            emotion, emotion_confidence = await self.analyze_emotion(input_text, user_id)
            
            # Detect crisis
            is_crisis, crisis_level = await self.detect_crisis(input_text, user_id)
            
            # Create therapy context
            context = TherapyContext(
                user_id=user_id,
                session_id=session_id,
                input_text=input_text,
                emotion=emotion,
                emotion_confidence=emotion_confidence,
                crisis_level=crisis_level,
                relevant_memories=relevant_memories or [],
                session_summary=session_summary
            )
            
            # Generate response
            response = await self.generate_therapy_response(context, conversation_history)
            
            # Return comprehensive result
            return {
                "response": response,
                "emotion": emotion.value if emotion else None,
                "emotion_confidence": emotion_confidence,
                "is_crisis": is_crisis,
                "crisis_level": crisis_level.value if crisis_level else None,
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
                "emotion_confidence": 0.0,
                "is_crisis": False,
                "crisis_level": None,
                "context": None
            }


# Global therapy service instance
_therapy_service = TherapyService()


def get_therapy_service() -> TherapyService:
    """Get the global therapy service instance."""
    return _therapy_service
