# app/api/websocket/chat.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.auth_services import SupabaseAuthService
from backend.services.graph_services import run_therapy_flow

router = APIRouter()

@router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        # Step 1: Authenticate and validate initial data BEFORE accepting the connection
        init_data = await websocket.receive_json()
        access_token = init_data.get("access_token")
        thread_id = init_data.get("thread_id", "default")

        # Validate required fields
        if not access_token:
            await websocket.close(
                code=4000,
                reason="Access token and input text are required"
            )
            return

        user = SupabaseAuthService.verify_jwt(access_token)
        user_id = getattr(user, "id", None)
        if not user_id:
            await websocket.close(code=4000, reason="Invalid access token")
            return


        print(f"WebSocket connection established for user {user_id} with thread {thread_id}")
  
        # Step 2: Process incoming messages
        async for message in websocket.iter_json():
            input_text = message.get("input")
            if input_text:
                if not await send_therapy_response(websocket, user_id, input_text, thread_id):
                    break
            else:
                await websocket.send_json({"error": "Invalid message format"})

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        import traceback
        traceback.print_exc()
        await websocket.send_json({"error": str(e)})
        await websocket.close()

async def send_therapy_response(websocket: WebSocket, user_id: str, input_text: str, thread_id: str) -> bool:
    try:
        result = run_therapy_flow(user_id=user_id, user_input=input_text, thread_id=thread_id)
        if not result:
            await websocket.send_json({"error": "Failed to run therapy flow"})
            await websocket.close(code=5000, reason="Internal server error")
            return False
        
        response = {
            "response": result.get("response"),
            # "relevant_memories": result.get("relevant_memories"),
            "emotion": result.get("emotion"),
            "is_crisis": result.get("is_crisis"),
            "mode": result.get("mode"),
            "journal_entry": result.get("journal_entry"),
            "attack": result.get("attack"),
        }
        
        await websocket.send_json(response)
        return True
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        return False
