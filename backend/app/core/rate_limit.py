"""Per-IP rate limiting via slowapi.

Limits are intentionally generous in dev (env-controlled). In tests they're
suppressed by setting ``RATE_LIMIT_ENABLED=false`` so the suite isn't flaky.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings


def _key(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return get_remote_address(request)


_storage_uri = settings.REDIS_URL if settings.RATE_LIMIT_USE_REDIS else "memory://"

limiter = Limiter(
    key_func=_key,
    default_limits=[],
    enabled=settings.RATE_LIMIT_ENABLED,
    storage_uri=_storage_uri,
    # Disabled: would require every limited endpoint to declare a starlette
    # Response parameter, which complicates handler signatures. The
    # 429 + Retry-After response we return on overflow is enough for clients.
    headers_enabled=False,
)


def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):  # noqa: ARG001
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down.",
                 "retry_after": getattr(exc, "retry_after", None)},
    )


# Reusable limit strings (env-overridable so ops can tune without redeploys).
LOGIN_LIMIT = settings.RL_LOGIN
REGISTER_LIMIT = settings.RL_REGISTER
PASSWORD_RESET_LIMIT = settings.RL_PASSWORD_RESET
INCIDENT_SUBMIT_LIMIT = settings.RL_INCIDENT_SUBMIT
