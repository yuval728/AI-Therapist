# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth
from websocket_routes import chat
app = FastAPI()

# Allow CORS (customize origin in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
# app.include_router(journal.router, prefix="/journal", tags=["Journal"])

@app.get("/")
def root():
    return {"message": "AI Therapist API is live."}
