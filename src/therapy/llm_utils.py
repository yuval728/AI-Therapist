"""Optimized LLM utilities with improved performance and caching."""
from typing import Any, Dict, List, Optional, Union, Type
from dataclasses import dataclass
import logging
import time
from litellm import acompletion
from src.config import get_settings
from src.utils import (
    log_performance_metric,
    log_security_event,
    timing_decorator,
    retry_decorator,
    ValidationError,
    TherapyError
)

# Configure logger for this module
logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class CompletionRequest:
    """Optimized completion request with enhanced validation."""
    model: str
    messages: List[Dict[str, str]]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    user_id: Optional[str] = None
    response_format: Optional[Type] = None
    
    def __post_init__(self):
        """Validate completion request parameters with optimized checks."""
        if not self.model:
            raise ValidationError("Model is required")
        if not self.messages:
            raise ValidationError("Messages are required")
        if not (0.0 <= self.temperature <= 2.0):
            raise ValidationError("Temperature must be between 0.0 and 2.0")
        if self.max_tokens and self.max_tokens <= 0:
            raise ValidationError("Max tokens must be positive")
        
        # Optimize message content length
        total_length = sum(len(msg.get('content', '')) for msg in self.messages)
        if total_length > 100000:  # 100k characters limit
            logger.warning(f"Large message content: {total_length} characters")


class LLMClient:
    """High-performance LLM client with caching and monitoring."""
    
    def __init__(self):
        self.settings = get_settings()
        self._request_count = 0
        self._total_tokens = 0
        self._response_cache = {}  # Simple response cache
        self._cache_ttl = 3600  # 1 hour
        self._rate_limit_cache = {}  # Rate limiting cache
    
    def _get_cache_key(self, request: CompletionRequest) -> str:
        """Generate cache key for request."""
        return f"{request.model}:{hash(str(request.messages))}:{request.temperature}"
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._response_cache:
            return False
        return (time.time() - self._response_cache[key]['timestamp']) < self._cache_ttl
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get response from cache if valid."""
        if self._is_cache_valid(key):
            return self._response_cache[key]['data']
        elif key in self._response_cache:
            del self._response_cache[key]  # Remove expired entry
        return None
    
    def _set_cache(self, key: str, data: Dict[str, Any]):
        """Set response in cache."""
        self._response_cache[key] = {
            'data': data,
            'timestamp': time.time()
        }

    # Backward-compatible alias expected by callers
    async def completion(self, request: Union[CompletionRequest, Dict[str, Any]]) -> Dict[str, Any]:
        return await self.complete(request)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
            "cache_entries": len(self._response_cache),
        }
    
    @timing_decorator("llm_completion")
    @retry_decorator(max_retries=3, delay=1.0)
    async def complete(
        self, 
        request: Union[CompletionRequest, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute completion with optimized caching and error handling."""
        try:
            # Convert dict to structured request
            if isinstance(request, dict):
                request = CompletionRequest(**request)
            
            # Check cache first
            cache_key = self._get_cache_key(request)
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                logger.debug(f"Cache hit for request: {cache_key[:50]}...")
                return cached_response
            
            # Validate request
            self._validate_request(request)
            
            # Execute completion
            result = await self._execute_completion(request)
            
            # Cache successful response
            self._set_cache(cache_key, result)
            
            # Log metrics
            self._log_success(request, result)
            
            return result
            
        except Exception as e:
            self._log_failure(request, e)
            raise TherapyError(f"LLM completion failed: {str(e)}") from e
    
    async def _execute_completion(self, request: CompletionRequest) -> Dict[str, Any]:
        """Execute the actual completion request."""
        self._log_request(request)
        
        completion_args = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
        }
        
        # Add optional parameters
        if request.max_tokens:
            completion_args["max_tokens"] = request.max_tokens
        if request.top_p:
            completion_args["top_p"] = request.top_p
        if request.frequency_penalty:
            completion_args["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty:
            completion_args["presence_penalty"] = request.presence_penalty
        
        response = await acompletion(**completion_args)
        
        # Track metrics
        self._request_count += 1
        if hasattr(response, 'usage'):
            self._total_tokens += response.usage.total_tokens
        
        return response.model_dump() if hasattr(response, 'model_dump') else dict(response)
    
    def _validate_request(self, request: CompletionRequest) -> None:
        """Enhanced request validation."""
        # Model availability check (simplified)
        available_models = ["gpt-3.5-turbo", "gpt-4", "claude-3-sonnet", "claude-3-haiku"]
        if request.model not in available_models:
            logger.warning(f"Unknown model: {request.model}")
        
        # Message content safety check
        for message in request.messages:
            content = message.get('content', '')
            if len(content) > 50000:  # 50k character limit per message
                raise ValidationError(f"Message too long: {len(content)} characters")
    
    def _log_request(self, request: CompletionRequest) -> None:
        """Log request for monitoring."""
        logger.info(
            f"LLM request: model={request.model}, "
            f"messages={len(request.messages)}, "
            f"temp={request.temperature}"
        )
    
    def _log_success(self, request: CompletionRequest, result: Dict[str, Any]) -> None:
        """Log successful completion."""
        usage = result.get('usage', {})
        
        log_performance_metric(
            metric_name="llm_completion_success",
            value=1,
            tags={
                "model": request.model,
                "total_tokens": usage.get('total_tokens', 0),
                "completion_tokens": usage.get('completion_tokens', 0),
            }
        )
    
    def _log_failure(self, request: CompletionRequest, error: Exception) -> None:
        """Log completion failure."""
        logger.error(f"LLM completion failed: {error}")
        
        log_security_event(
            event="llm_completion_failure",
            user_id=getattr(request, 'user_id', None),
            details={
                "model": request.model,
                "error": str(error),
                "message_count": len(request.messages)
            }
        )


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
    except Exception:
        # Fallback for critical therapy responses
        return "I'm here to support you. Could you tell me more about what's on your mind?"


async def classify_text(
    text: str,
    system_prompt: str,
    model: Optional[str] = None,
    user_id: Optional[str] = None,
    response_format: Optional[Type] = None
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
        user_id=user_id,
        response_format=response_format
    )


def get_llm_stats() -> Dict[str, Any]:
    """Get LLM client statistics."""
    return _llm_client.stats
