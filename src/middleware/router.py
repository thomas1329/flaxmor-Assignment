import httpx
from fastapi import APIRouter, Depends, Request, Response, HTTPException

from src.middleware.controller import get_models_controller, chat_completions_controller
from src.config import settings

v1_router = APIRouter(prefix="/v1")
health_router = APIRouter()

def get_http_client(request):
    return request.app.state.http_client

@health_router.get("/health")
async def health():
    return {"status": "ok"}

@health_router.get("/ready")
async def ready():
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured")
    return {"status": "ready"}

@v1_router.get("/models")
async def list_models(client= Depends(get_http_client)):
    return await get_models_controller(client)

@v1_router.post("/chat/completions")
async def chat_completions(request, client = Depends(get_http_client)):
    return await chat_completions_controller(request, client)