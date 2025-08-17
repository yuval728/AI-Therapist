from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.services.auth_services import SupabaseAuthService
from src.services.graph_services import run_therapy_flow_async
from src.config.constants import Limits, ResponseMessages
from src.utils.response_formatter import format_streaming_response, create_error_response, create_delta_response, create_end_response
from loguru import logger
import time
from collections import defaultdict, deque
from typing import Dict, Any, Optional
from src.observability.metrics import ws_messages_total, ws_errors_total, crisis_events_total, response_latency_seconds

# Simple in-memory rate limiter (token bucket per user_id)
_buckets = defaultdict(lambda: deque())  # stores timestamps

router = APIRouter()

@router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    try:
        init_data = await websocket.receive_json()
        access_token = init_data.get("access_token")
        thread_id = init_data.get("thread_id", "default")
        if not access_token:
            await websocket.close(code=Limits.WS_MISSING_TOKEN, reason=ResponseMessages.MISSING_ACCESS_TOKEN)
            return
        user = SupabaseAuthService.verify_jwt(access_token)
        user_id = getattr(user, "id", None)
        if not user_id:
            await websocket.close(code=Limits.WS_INVALID_TOKEN, reason=ResponseMessages.INVALID_TOKEN)
            return
        await websocket.accept()
        logger.info(f"ws_connected user={user_id} thread={thread_id}")
        await websocket.send_json({"event": "start", "thread_id": thread_id})
        async for message in websocket.iter_json():
            input_text = message.get("input")
            if not input_text:
                await websocket.send_json(create_error_response(ResponseMessages.INVALID_MESSAGE))
                continue
            # rate limiting
            now = time.time()
            bucket = _buckets[user_id]
            while bucket and now - bucket[0] > 60:
                bucket.popleft()
            if len(bucket) >= Limits.RATE_LIMIT_PER_MIN:
                await websocket.send_json(create_error_response(ResponseMessages.RATE_LIMIT_EXCEEDED))
                continue
            bucket.append(now)
            if not await send_therapy_response(websocket, user_id, input_text, thread_id):
                break
    except WebSocketDisconnect:
        logger.info("ws_disconnected")
    except Exception as e:  # noqa
        logger.exception("ws_error")
        try:
            await websocket.send_json(create_error_response(str(e)))
        finally:
            await websocket.close()

async def send_therapy_response(websocket: WebSocket, user_id: str, input_text: str, thread_id: str) -> bool:
    try:
        start = time.time()
        result = await run_therapy_flow_async(user_id=user_id, user_input=input_text, thread_id=thread_id)
        if not result:
            await websocket.send_json(create_error_response(ResponseMessages.THERAPY_FLOW_FAILED))
            await websocket.close(code=Limits.WS_INTERNAL_ERROR, reason=ResponseMessages.INTERNAL_SERVER_ERROR)
            return False
        
        full_response = result.get("response") or ""
        formatted_chunks = format_streaming_response(full_response)
        
        for chunk in formatted_chunks:
            await websocket.send_json(create_delta_response(chunk))
        latency = time.time() - start
        response_latency_seconds.labels(user_id=user_id, thread_id=thread_id).observe(latency)
        if result.get("is_crisis"):
            crisis_events_total.labels(user_id=user_id, thread_id=thread_id).inc()
        ws_messages_total.labels(user_id=user_id, thread_id=thread_id).inc()
        await websocket.send_json(create_end_response(
            full_response,
            emotion=result.get("emotion"),
            is_crisis=result.get("is_crisis"),
            mode=result.get("mode"),
            journal_entry=result.get("journal_entry"),
            attack=result.get("attack")
        ))
        return True
    except Exception as e:
        ws_errors_total.labels(user_id=user_id, thread_id=thread_id).inc()
        await websocket.send_json(create_error_response(str(e)))
        return False
