import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

import asyncio
from contextlib import asynccontextmanager

from app.api.v1 import analytics, auth, dashboard, events, forms, map as map_api, org, person_types, reviews, submissions, uploads
from app.core.config import get_settings
from app.core.db import engine
from app.core.logging import configure_logging
from app.workers.geocode import run_geocode_worker
from app.workers.outbox import run_worker

configure_logging()
log = logging.getLogger("fieldsync")
settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    stop = asyncio.Event()
    tasks = [asyncio.create_task(run_worker(stop)), asyncio.create_task(run_geocode_worker(stop))]
    yield
    stop.set()
    for t in tasks:
        t.cancel()


app = FastAPI(title="FieldSync API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"],
)


MAX_JSON_BODY = 1024 * 1024


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    """Reject oversized requests up front (Content-Length). Photo chunks get the upload limit; the
    upload handler additionally refuses bytes beyond the size declared at initiate."""
    declared = request.headers.get("content-length")
    is_upload = request.method == "PUT" and request.url.path.startswith("/api/v1/uploads/")
    limit = settings.max_upload_bytes if is_upload else MAX_JSON_BODY
    if declared and declared.isdigit() and int(declared) > limit:
        return JSONResponse({"detail": "Request body too large"}, status_code=413)
    return await call_next(request)


@app.middleware("http")
async def correlation_and_timing(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled error", extra={"correlation_id": cid, "path": request.url.path})
        return JSONResponse({"detail": "Internal server error", "correlation_id": cid}, status_code=500)
    ms = (time.perf_counter() - start) * 1000
    response.headers["X-Correlation-ID"] = cid
    log.info(
        "request",
        extra={
            "correlation_id": cid,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(ms, 1),
        },
    )
    return response


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}


@app.get("/ready", tags=["ops"])
async def ready():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return {"status": "ready"}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(org.router, prefix="/api/v1")
app.include_router(forms.agent_router, prefix="/api/v1")
app.include_router(forms.internal_router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(submissions.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(person_types.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(map_api.router, prefix="/api/v1")
