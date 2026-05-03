import time
import logging
import os
import threading
from datetime import datetime
from typing import Dict, Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.monitoring")

_metrics_lock = threading.Lock()
_requests_total = 0
_errors_total = 0
_response_times: list = []
_db_size_mb: float = 0.0
_start_time = time.time()


def _get_db_path() -> str:
    database_url = os.getenv("DATABASE_URL", "sqlite:///atlas_v2.db")
    if database_url.startswith("sqlite:///"):
        path = database_url.replace("sqlite:///", "")
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        return path
    return ""


def _compute_db_size_mb() -> float:
    db_path = _get_db_path()
    if db_path and os.path.exists(db_path):
        return round(os.path.getsize(db_path) / (1024 * 1024), 2)
    return 0.0


def get_metrics() -> Dict[str, Any]:
    global _requests_total, _errors_total, _response_times, _db_size_mb, _start_time

    with _metrics_lock:
        avg_rt = (
            sum(_response_times) / len(_response_times)
            if _response_times
            else 0.0
        )
        uptime = int(time.time() - _start_time)
        db_size = _compute_db_size_mb()

    return {
        "requests_total": _requests_total,
        "errors_total": _errors_total,
        "avg_response_time_ms": round(avg_rt, 2),
        "db_size_mb": db_size,
        "uptime_seconds": uptime,
    }


class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        global _requests_total, _errors_total, _response_times

        start = time.time()

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            with _metrics_lock:
                _requests_total += 1
                _errors_total += 1
            elapsed = (time.time() - start) * 1000
            with _metrics_lock:
                _response_times.append(elapsed)
                if len(_response_times) > 1000:
                    _response_times = _response_times[-500:]
            logger.error(
                "request_error",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "elapsed_ms": round(elapsed, 2),
                    "error": str(exc),
                },
            )
            raise

        elapsed = (time.time() - start) * 1000

        with _metrics_lock:
            _requests_total += 1
            if response.status_code >= 500:
                _errors_total += 1
            _response_times.append(elapsed)
            if len(_response_times) > 1000:
                _response_times = _response_times[-500:]

        if elapsed > 2000:
            logger.warning(
                "slow_request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "elapsed_ms": round(elapsed, 2),
                },
            )
        else:
            logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "elapsed_ms": round(elapsed, 2),
                },
            )

        response.headers["X-Response-Time-ms"] = str(round(elapsed, 2))
        return response
