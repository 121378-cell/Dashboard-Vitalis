import time
import threading
from typing import Dict, Optional, Tuple

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class _TokenBucket:
    __slots__ = ("max_tokens", "refill_rate", "tokens", "last_refill", "lock")

    def __init__(self, max_tokens: int, refill_per_sec: float):
        self.max_tokens = max_tokens
        self.refill_rate = refill_per_sec
        self.tokens = float(max_tokens)
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def consume(self) -> bool:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.max_tokens, self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False

    def retry_after(self) -> float:
        with self.lock:
            deficit = 1.0 - self.tokens
            if deficit <= 0:
                return 0
            return round(deficit / self.refill_rate, 1)


_RATE_LIMITS: Dict[str, Tuple[int, int]] = {
    "POST:/api/v1/ai/chat": (30, 60),
    "POST:/api/v1/sync/garmin": (10, 3600),
    "POST:/api/v1/auth/garmin/login": (5, 3600),
}

_buckets: Dict[str, _TokenBucket] = {}
_buckets_lock = threading.Lock()


def _get_bucket(key: str, max_requests: int, window_seconds: int) -> _TokenBucket:
    with _buckets_lock:
        if key not in _buckets:
            refill = max_requests / window_seconds
            _buckets[key] = _TokenBucket(max_requests, refill)
        return _buckets[key]


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _get_user_id(request: Request) -> str:
    uid = request.headers.get("x-user-id")
    if uid:
        return uid
    auth = request.headers.get("authorization", "")
    if auth:
        return auth[-20:]
    return _get_client_ip(request)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method.upper()
        path = request.url.path.rstrip("/")

        limit_key = f"{method}:{path}"

        matched_rule: Optional[str] = None
        for rule_key in _RATE_LIMITS:
            rule_method, rule_path = rule_key.split(":", 1)
            if rule_method == method and (
                path == rule_path.rstrip("/") or path.startswith(rule_path.rstrip("/") + "/")
            ):
                matched_rule = rule_key
                break

        if matched_rule:
            max_req, window_sec = _RATE_LIMITS[matched_rule]

            if "login" in matched_rule:
                identity = f"ip:{_get_client_ip(request)}"
            else:
                identity = f"user:{_get_user_id(request)}"

            bucket_key = f"{matched_rule}:{identity}"
            bucket = _get_bucket(bucket_key, max_req, window_sec)

            if not bucket.consume():
                retry = bucket.retry_after()
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Retry after {retry}s.",
                    headers={"Retry-After": str(int(retry))},
                )

        return await call_next(request)
