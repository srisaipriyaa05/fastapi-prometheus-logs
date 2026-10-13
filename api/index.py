import json
import logging
import os
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

EMAIL = os.getenv("USER_EMAIL", "24f2007077@ds.study.iitm.ac.in")
START_TIME = time.monotonic()
LOG_LIMIT = 1000

# A single process-local Prometheus registry is live and updated per request.
HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests received by the application.",
    ["method", "path", "status"],
)

_log_entries: deque[dict[str, Any]] = deque(maxlen=LOG_LIMIT)
_log_lock = Lock()


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        item = getattr(record, "structured", {})
        return json.dumps(item, separators=(",", ":"), ensure_ascii=False)


logger = logging.getLogger("request_json")
logger.setLevel(logging.INFO)
logger.propagate = False
_stream = logging.StreamHandler()
_stream.setFormatter(JSONFormatter())
logger.handlers.clear()
logger.addHandler(_stream)


def record_request(level: str, path: str, request_id: str, method: str, status: int, duration_ms: float):
    entry = {
        "level": level,
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": path,
        "request_id": request_id,
        "method": method,
        "status": status,
        "duration_ms": round(duration_ms, 3),
    }
    with _log_lock:
        _log_entries.append(entry)
    logger.info("request", extra={"structured": entry})


class RequestMetricsAndLogsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.monotonic()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            path = request.url.path
            HTTP_REQUESTS.labels(request.method, path, str(status_code)).inc()
            record_request(
                "error" if status_code >= 500 else "info",
                path,
                request_id,
                request.method,
                status_code,
                duration_ms,
            )


app = FastAPI(title="Prometheus Instrumented Work API")
app.add_middleware(RequestMetricsAndLogsMiddleware)


@app.get("/work")
def work(n: int = 1):
    # Keep the endpoint bounded so accidental large n values cannot stall the service.
    if n < 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="n must be non-negative")
    if n > 1_000_000:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="n is too large")
    done = 0
    for _ in range(n):
        done += 1
    return {"email": EMAIL, "done": done}


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": max(0.0, time.monotonic() - START_TIME)}


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


@app.get("/logs/tail")
def logs_tail(limit: int = 100):
    limit = max(0, min(limit, LOG_LIMIT))
    with _log_lock:
        entries = list(_log_entries)
    return entries[-limit:] if limit else []
