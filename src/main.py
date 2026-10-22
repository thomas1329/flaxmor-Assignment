import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request

from src.config import settings
from src.middleware.logger import logger, request_id_var
from src.middleware.router import v1_router, health_router

@asynccontextmanager
async def lifespan(app):
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.openai_base_url.rstrip("/"),
        timeout=httpx.Timeout(settings.upstream_timeout, connect=10.0),
    )
    logger.info("Middleware started", extra={"upstream": settings.openai_base_url})
    yield
    await app.state.http_client.aclose()
    logger.info("Middleware stopped")

app = FastAPI(title="OpenAI Proxy Middleware", lifespan=lifespan)

@app.middleware("http")
async def log_requests(request, call_next):
    req_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:8]
    token = request_id_var.set(req_id)
    start = time.perf_counter()

    logger.info("Request started", extra={"method": request.method, "path": request.url.path})
    try:
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = req_id
        logger.info("Request finished", extra={"status": response.status_code, "duration_ms": elapsed_ms})
        return response
    except Exception:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception("Unhandled error", extra={"duration_ms": elapsed_ms})
        raise
    finally:
        request_id_var.reset(token)

app.include_router(health_router)
app.include_router(v1_router)