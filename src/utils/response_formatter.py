"""Response formatting utilities for consistent message handling."""
from typing import List

def format_streaming_response(full_response: str) -> List[str]:
    """Format response for streaming by splitting into sentences."""
    if not full_response:
        return []
    
    sentences = [s.strip() for s in full_response.split('.') if s.strip()]
    formatted_chunks = []
    
    for i, chunk in enumerate(sentences):
        # Add period back except for the last sentence
        formatted_chunk = chunk + ('.' if i < len(sentences) - 1 else '')
        formatted_chunks.append(formatted_chunk)
    
    return formatted_chunks

def create_websocket_response(event: str, **data) -> dict:
    """Create standardized websocket response format."""
    response = {"event": event}
    response.update(data)
    return response

def create_error_response(error_message: str) -> dict:
    """Create standardized error response."""
    return create_websocket_response("error", error=error_message)

def create_delta_response(delta: str) -> dict:
    """Create standardized delta response for streaming."""
    return create_websocket_response("delta", delta=delta)

def create_end_response(response: str, **metadata) -> dict:
    """Create standardized end response with metadata."""
    return create_websocket_response("end", response=response, **metadata)
