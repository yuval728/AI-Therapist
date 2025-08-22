"""WebSocket chat routes for real-time therapy conversations."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from typing import Dict, Any, Optional, List
import time
import json
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone

from src.services import get_auth_service, get_session_service
from src.therapy.graphs.therapy_flow import build_therapy_graph
from src.models import (
    TherapySession, SessionMessage, EmotionType, CrisisLevel,
    MessageType, APIResponse
)
from src.utils import log_therapy_event, timing_decorator
from src.config import get_settings

# WebSocket connection manager
class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
    
    async def connect(self, websocket: WebSocket, user_id: str, session_id: str):
        """Accept WebSocket connection."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_sessions[user_id] = session_id
        
        log_therapy_event(
            event="websocket_connected",
            user_id=user_id,
            session_id=session_id
        )
    
    def disconnect(self, user_id: str):
        """Remove WebSocket connection."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        
        log_therapy_event(
            event="websocket_disconnected",
            user_id=user_id
        )
    
    async def send_message(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user."""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_json(message)
    
    async def send_error(self, user_id: str, error: str, error_code: str = "ERROR"):
        """Send error message to user."""
        await self.send_message(user_id, {
            "type": "error",
            "error": error,
            "error_code": error_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


manager = ConnectionManager()
router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/chat")
async def chat_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time therapy chat."""
    user_id = None
    session_id = None
    
    try:
        # Wait for authentication message
        auth_data = await websocket.receive_json()
        access_token = auth_data.get("access_token")
        session_id = auth_data.get("session_id")
        
        if not access_token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing access token")
            return
        
        # Authenticate user
        auth_service = await get_auth_service()
        auth_result = await auth_service.get_current_user(access_token)
        
        if not auth_result.success:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return
        
        user_id = auth_result.data["user"]["id"]
        
        # Create or get session
        if not session_id:
            session_service = await get_session_service()
            session_result = await session_service.create_session(user_id)
            if not session_result.success:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Session creation failed")
                return
            # The model uses `id` as the identifier; DB stores it in `session_id`
            session_id = session_result.data.id
        
        # Connect to manager
        await manager.connect(websocket, user_id, session_id)
        
        # Send connection confirmation
        await manager.send_message(user_id, {
            "type": "connected",
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Handle messages
        async for message in websocket.iter_json():
            await handle_chat_message(user_id, session_id, message)
            
    except WebSocketDisconnect:
        if user_id:
            manager.disconnect(user_id)
    except Exception as e:
        log_therapy_event(
            event="websocket_error",
            user_id=user_id,
            session_id=session_id,
            error=str(e)
        )
        if user_id:
            await manager.send_error(user_id, "Connection error occurred")
            manager.disconnect(user_id)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass

async def handle_chat_message(user_id: str, session_id: str, message: Dict[str, Any]):
    """Handle incoming chat message from WebSocket."""
    try:
        message_type = message.get("type")
        
        if message_type == "chat":
            await handle_therapy_message(user_id, session_id, message)
        elif message_type == "ping":
            await manager.send_message(user_id, {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
        else:
            await manager.send_error(user_id, f"Unknown message type: {message_type}", "INVALID_MESSAGE_TYPE")
            
    except Exception as e:
        log_therapy_event(
            event="message_handling_error",
            user_id=user_id,
            session_id=session_id,
            error=str(e)
        )
        await manager.send_error(user_id, "Failed to process message")


@timing_decorator("therapy_websocket_response")
async def handle_therapy_message(user_id: str, session_id: str, message: Dict[str, Any]):
    """Process therapy message through the therapy flow."""
    try:
        user_input = message.get("content", "").strip()
        
        if not user_input:
            await manager.send_error(user_id, "Message content cannot be empty", "EMPTY_MESSAGE")
            return
        
        
        # Send typing indicator
        await manager.send_message(user_id, {
            "type": "typing",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Build therapy graph and process message
        therapy_graph = build_therapy_graph()
        
        # Create initial state
        initial_state = {
            "user_id": user_id,
            "session_id": session_id,
            "user_input": user_input,
            "messages": [],
            "emotion": "neutral",
            "crisis_level": "none",
            "mode": "chat",
            "response": "",
            "metadata": {}
        }
        
        # Process through therapy flow
        result = await therapy_graph.ainvoke(initial_state)
        
        # Send response in chunks for streaming effect
        response_text = result.get("response", "")
        await stream_response(user_id, session_id, response_text, result)
        
        # Log successful interaction
        log_therapy_event(
            event="therapy_message_processed",
            user_id=user_id,
            session_id=session_id,
            emotion=result.get("emotion"),
            crisis_level=result.get("crisis_level"),
            mode=result.get("mode")
        )
        
    except Exception as e:
        log_therapy_event(
            event="therapy_message_error",
            user_id=user_id,
            session_id=session_id,
            error=str(e)
        )
        await manager.send_error(user_id, "Failed to process therapy message")


async def stream_response(user_id: str, session_id: str, response_text: str, result: Dict[str, Any]):
    """Stream response text in chunks to simulate typing."""
    try:
        # Split response into words for streaming
        words = response_text.split()
        chunk_size = 3  # Send 3 words at a time
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            
            await manager.send_message(user_id, {
                "type": "response_chunk",
                "content": chunk,
                "is_final": False,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Small delay for typing effect
            await asyncio.sleep(0.1)
        
        # Send final message with metadata
        await manager.send_message(user_id, {
            "type": "response_complete",
            "content": response_text,
            "is_final": True,
            "emotion": result.get("emotion"),
            "crisis_level": result.get("crisis_level"),
            "mode": result.get("mode"),
            "metadata": result.get("metadata", {}),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        log_therapy_event(
            event="response_streaming_error",
            user_id=user_id,
            session_id=session_id,
            error=str(e)
        )
        await manager.send_error(user_id, "Failed to send response")


# Health check for WebSocket
@router.websocket("/health")
async def websocket_health(websocket: WebSocket):
    """WebSocket health check endpoint."""
    await websocket.accept()
    await websocket.send_json({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_connections": len(manager.active_connections)
    })
    await websocket.close()
