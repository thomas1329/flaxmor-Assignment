import json
import httpx
from fastapi import Request, Response, HTTPException
from fastapi.responses import StreamingResponse

from src.middleware.logger import logger
from src.middleware.handler import (
    fetch_models, 
    forward_chat_completion, 
    stream_chat_completion, 
    prepend_system_prompt
)

async def get_models_controller(client):
    try:
        resp = await fetch_models(client)
        resp.raise_for_status()
        return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch models", extra={"error": str(exc)})
        fallback = {
            "object": "list",
            "data": [
                {"id": "gpt-4o-mini", "object": "model", "created": 1721172741, "owned_by": "openai"},
                {"id": "gpt-4o", "object": "model", "created": 1715368132, "owned_by": "openai"},
            ],
        }
        return Response(content=json.dumps(fallback), media_type="application/json")

async def chat_completions_controller(request, client):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict) or "messages" not in body:
        raise HTTPException(status_code=422, detail="Missing 'messages' field")

    try:
        body["messages"] = prepend_system_prompt(body["messages"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    is_stream = bool(body.get("stream", False))
    logger.info("Forwarding to OpenAI", extra={"model": body.get("model"), "stream": is_stream, "msg_count": len(body["messages"])})

    if not is_stream:
        try:
            resp = await forward_chat_completion(client, body)
        except httpx.TimeoutException:
            logger.error("OpenAI request timed out")
            raise HTTPException(status_code=504, detail="Upstream request timed out")
        except httpx.RequestError as exc:
            logger.error("OpenAI request failed", extra={"error": str(exc)})
            raise HTTPException(status_code=502, detail="Failed to connect to OpenAI")

        if resp.status_code >= 400:
            logger.error("OpenAI error response", extra={"status": resp.status_code, "body": resp.text[:300]})
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")

    return StreamingResponse(
        stream_chat_completion(client, body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )