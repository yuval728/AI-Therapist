# app/api/websocket/chat.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from services.auth_services import get_current_user, SupabaseAuthService
from services.graph_services import run_therapy_flow

router = APIRouter()

@router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()

    try:
        # Step 1: Receive the first message (must include access_token, input, thread_id)
        init_data = await websocket.receive_json()
        access_token = init_data.get("access_token")
        if not access_token:
            await websocket.close(code=4000, reason="Access token is required")
            return
        user = await SupabaseAuthService.verify_jwt(access_token)
        user_id = user.id if user else None

        if not user_id:
            await websocket.close(code=4000, reason="Invalid access token")
            return
        
        input_text = init_data.get("input")
        thread_id = init_data.get("thread_id", "default")
        if not input_text:
            await websocket.close(code=4000, reason="Input text is required")
            return


        # Step 2: Run the therapy flow
        result = await run_therapy_flow(user_id=user_id, user_input=input_text, thread_id=thread_id)
        if not result:
            await websocket.send_json({"error": "Failed to run therapy flow"})
            await websocket.close(code=5000, reason="Internal server error")
            return
        await websocket.send_json(result)
        

        while True:
            message = await websocket.receive_json()
            if "input" in message:
                input_text = message["input"]
                # Run the therapy flow again with the new input
                result = await run_therapy_flow(user_id=user_id, user_input=input_text, thread_id=thread_id)
                if not result:
                    await websocket.send_json({"error": "Failed to run therapy flow"})
                    continue
                await websocket.send_json(result)
            else:
                await websocket.send_json({"error": "Invalid message format"})

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()
