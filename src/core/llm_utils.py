"""Enhanced LLM utilities with comprehensive error handling and monitoring."""
import asyncio
import time
from typing import Callable, Any, Dict, List, Optional, Union
from dataclasses import dataclass
from litellm import completion
from src.config import get_settings
from src.utils import (
    log_performance_metric,
    log_security_event,
    timing_decorator,
    retry_decorator,
    ValidationError,
    TherapyError
)

settings = get_settings()


@dataclass
class CompletionRequest:
    """Structured completion request with validation."""
    model: str
    messages: List[Dict[str, str]]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    user_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate completion request parameters."""
        if not self.model:
            raise ValidationError("Model is required")
        if not self.messages:
            raise ValidationError("Messages are required")
        if not (0.0 <= self.temperature <= 2.0):
            raise ValidationError("Temperature must be between 0.0 and 2.0")
        if self.max_tokens and self.max_tokens <= 0:
            raise ValidationError("Max tokens must be positive")


class LLMClient:
    """Enhanced LLM client with monitoring and safety features."""
    
    def __init__(self):
        self.settings = get_settings()
        self._request_count = 0
        self._total_tokens = 0
    
    @timing_decorator("llm_completion")
    @retry_decorator(max_attempts=3, delay=1.0, backoff=2.0)
    async def completion(
        self,
        request: Union[CompletionRequest, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute LLM completion with comprehensive monitoring."""
        # Convert dict to CompletionRequest if needed
        if isinstance(request, dict):
            request = CompletionRequest(**request)
        
        # Validate request
        self._validate_request(request)
        
        # Log request
        self._log_request(request)
        
        try:
            # Execute completion
            result = await self._execute_completion(request)
            
            # Log success metrics
            self._log_success(request, result)
            
            return result
            
        except Exception as e:
            # Log failure
            self._log_failure(request, e)
            raise TherapyError(f"LLM completion failed: {str(e)}")
    
    async def _execute_completion(self, request: CompletionRequest) -> Dict[str, Any]:
        """Execute the actual completion request."""
        completion_kwargs = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
        }
        
        # Add optional parameters
        if request.max_tokens:
            completion_kwargs["max_tokens"] = request.max_tokens
        if request.top_p:
            completion_kwargs["top_p"] = request.top_p
        if request.frequency_penalty:
            completion_kwargs["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty:
            completion_kwargs["presence_penalty"] = request.presence_penalty
        
        # Execute in thread pool to avoid blocking
        return await asyncio.to_thread(completion, **completion_kwargs)
    
    def _validate_request(self, request: CompletionRequest) -> None:
        """Validate completion request for safety and compliance."""
        # Check for potential prompt injection
        for message in request.messages:
            content = message.get("content", "")
            if self._detect_prompt_injection(content):
                log_security_event(
                    event="prompt_injection_in_llm_request",
                    attack_type="prompt_injection",
                    user_id=request.user_id,
                    severity="HIGH"
                )
                raise ValidationError("Potential prompt injection detected")
        
        # Check token limits with more accurate estimation
        estimated_tokens = self._estimate_tokens(request.messages)
        if estimated_tokens > self.settings.models.max_tokens_chat:
            raise ValidationError(f"Request exceeds token limit: {estimated_tokens}")
    
    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """More accurate token estimation."""
        # Rough approximation: 1 token ≈ 0.75 words
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return int(total_chars / 3)  # Conservative estimate
    
    def _detect_prompt_injection(self, content: str) -> bool:
        """Enhanced prompt injection detection with configurable patterns."""
        injection_patterns = [
            "ignore previous instructions", "disregard above", "act as", "simulate",
            "pretend to be", "jailbreak", "you are now", "forget everything",
            "new instructions", "override", "system prompt", "developer mode"
        ]
        content_lower = content.lower()
        return any(pattern in content_lower for pattern in injection_patterns)
    
    def _log_request(self, request: CompletionRequest) -> None:
        """Log completion request details."""
        self._request_count += 1
        log_performance_metric(
            operation="llm_request_initiated",
            duration_ms=0,
            user_id=request.user_id,
            model=request.model,
            temperature=request.temperature,
            message_count=len(request.messages)
        )
    
    def _log_success(self, request: CompletionRequest, result: Dict[str, Any]) -> None:
        """Log successful completion metrics."""
        usage = result.get("usage", {})
        tokens_used = usage.get("total_tokens", 0)
        self._total_tokens += tokens_used
        
        log_performance_metric(
            operation="llm_completion_success",
            duration_ms=0,  # Duration handled by timing decorator
            user_id=request.user_id,
            model=request.model,
            tokens_used=tokens_used,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0)
        )
    
    def _log_failure(self, request: CompletionRequest, error: Exception) -> None:
        """Log completion failure."""
        log_performance_metric(
            operation="llm_completion_failure",
            duration_ms=0,
            success=False,
            user_id=request.user_id,
            model=request.model,
            error=str(error)
        )
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "request_count": self._request_count,
            "total_tokens": self._total_tokens
        }


# Global client instance
_llm_client = LLMClient()


async def get_completion(**kwargs) -> Dict[str, Any]:
    """Get LLM completion with validation and monitoring."""
    return await _llm_client.completion(kwargs)


async def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> str:
    """Simplified chat completion that returns just the content."""
    try:
        request = CompletionRequest(
            model=model or settings.models.chat_model,
            messages=messages,
            temperature=temperature or settings.models.temperature_chat,
            user_id=user_id,
            **kwargs
        )
        
        result = await _llm_client.completion(request)
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        # Fallback for critical therapy responses
        return "I'm here to support you. Could you tell me more about what's on your mind?"


async def classify_text(
    text: str,
    system_prompt: str,
    model: Optional[str] = None,
    user_id: Optional[str] = None
) -> str:
    """Classify text using LLM with consistent formatting."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text}
    ]
    
    return await chat_completion(
        messages=messages,
        model=model or settings.models.light_model,
        temperature=settings.models.temperature_classifiers,
        user_id=user_id
    )


def get_llm_stats() -> Dict[str, Any]:
    """Get LLM client statistics."""
    return _llm_client.stats
