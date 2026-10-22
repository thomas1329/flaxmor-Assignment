import json
import time
import uuid
from typing import Any, AsyncIterator
import httpx
from fastapi import HTTPException
from copy import deepcopy
from typing import Any

from src.config import settings
from src.prompts import SYSTEM_PROMPT
from src.middleware.logger import logger, request_id_var

def prepend_system_prompt(messages):
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")

    if not all(isinstance(m, dict) for m in messages):
        raise ValueError("each message must be a dictionary")

    existing_system = [
        m["content"]
        for m in messages
        if m.get("role") == "system"
        and isinstance(m.get("content"), str)
    ]

    other_messages = [
        deepcopy(m)
        for m in messages
        if m.get("role") != "system"
    ]

    prompt = SYSTEM_PROMPT

    if existing_system:
        prompt += (
            "Additional context from the caller:"
            + "".join(existing_system)
        )

    return [
        {"role": "system", "content": prompt},
        *other_messages,
    ]

def get_upstream_headers():
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Set your key")
    return {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

def make_sse_error(msg):
    data = {
        "id": f"chatcmpl-err-{uuid.uuid4().hex[:6]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "proxy",
        "choices": [{
            "index": 0,
            "delta": {"content": f"\n\n[Error: {msg}]"},
            "finish_reason": "stop",
        }],
    }
    return f"data: {json.dumps(data)}\n\ndata: [DONE]\n\n".encode("utf-8")

async def fetch_models(client):
    return await client.get("/models", headers=get_upstream_headers())

async def forward_chat_completion(client, body):
    return await client.post("/chat/completions", json=body, headers=get_upstream_headers())

async def stream_chat_completion(client, body):
    req_id = request_id_var.get()
    stream_start = time.perf_counter()
    token = request_id_var.set(req_id)
    
    try:
        async with client.stream("POST", "/chat/completions", json=body, headers=get_upstream_headers()) as resp:
            if resp.status_code >= 400:
                err_body = (await resp.aread()).decode("utf-8", errors="replace")
                logger.error("OpenAI stream rejected", extra={"status": resp.status_code, "body": err_body[:300]})
                yield make_sse_error(f"OpenAI HTTP {resp.status_code}")
                return

            async for chunk in resp.aiter_bytes():
                if chunk:
                    yield chunk
    except httpx.TimeoutException:
        logger.error("OpenAI stream timed out")
        yield make_sse_error("Upstream connection timed out")
    except httpx.RequestError as exc:
        logger.error("OpenAI stream dropped", extra={"error": str(exc)})
        yield make_sse_error("Connection to OpenAI failed")
    finally:
        duration_ms = round((time.perf_counter() - stream_start) * 1000, 2)
        logger.info("Stream completed", extra={"duration_ms": duration_ms})
        request_id_var.reset(token)