from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import auth
from .api.websocket_routes import chat
from .config.config import get_settings
from .core.logging_utils import configure_logging, log_event
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

settings = get_settings()
configure_logging()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])

@app.get("/healthz")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    log_event("root_access")
    return {"message": "AI Therapist API is live."}

@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
