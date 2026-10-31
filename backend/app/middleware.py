import time
import uuid
import logging
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.security_service import security_service, SecurityError
from app.services.metrics_service import metrics_service

logger = logging.getLogger("vidmind.middleware")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware generating or propagating X-Request-ID header.
    Tracks latency and records HTTP metrics in MetricsService.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id

        response = await call_next(request)

        duration = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        
        # Record metrics (skip health/ready from latency stats noise if desired, but record all)
        metrics_service.record_http_request(request.url.path, response.status_code, duration)
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Application-level sliding-window Rate Limiter Middleware.
    Pillar 1: Rate Limiting (Returns HTTP 429 when threshold exceeded).
    """
    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_records: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Exclude static/health check endpoints from rate limiting
        if request.url.path in ["/health", "/ready", "/", "/api/health"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        window_start = now - 60.0

        # Clean timestamps older than window
        timestamps = [t for t in self.client_records[client_ip] if t > window_start]
        self.client_records[client_ip] = timestamps

        if len(timestamps) >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please try again later.",
                        "request_id": getattr(request.state, "request_id", None)
                    }
                }
            )

        self.client_records[client_ip].append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies security headers to all outgoing responses.
    Pillar 1: Security Headers (nosniff, frame protection, CSP, referrer policy).
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' http: https: ws: wss:;"
        )
        return response


async def global_exception_handler(request: Request, exc: Exception):
    """
    Global Exception Handler:
    Catches all unhandled exceptions and security errors.
    Returns sanitized JSON errors without exposing raw stack traces, API keys, or server paths.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    if isinstance(exc, SecurityError):
        clean_msg = security_service.scrub_secrets(str(exc))
        status_code = status.HTTP_403_FORBIDDEN if "SSRF" in clean_msg or "Violation" in clean_msg else status.HTTP_400_BAD_REQUEST
        error_code = "FORBIDDEN" if status_code == 403 else "VALIDATION_ERROR"
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": clean_msg,
                    "request_id": request_id
                }
            }
        )

    # General Unhandled Exception
    scrubbed_err = security_service.scrub_secrets(str(exc))
    logger.error(f"[Unhandled Error][req_id={request_id}] {scrubbed_err}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected server error occurred. Please try again later.",
                "request_id": request_id
            }
        }
    )
