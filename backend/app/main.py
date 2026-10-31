import sys
import io

# Force Windows Console standard output & error streams to use UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import (
    health, projects, jobs, intents, artifacts,
    library, search, conversations, intelligence, agents
)
from app.middleware import (
    CorrelationIdMiddleware,
    RateLimiterMiddleware,
    SecurityHeadersMiddleware,
    global_exception_handler
)
from app.services.security_service import SecurityError

app = FastAPI(
    title=settings.app_name,
    description="VidMind API — AI Video Knowledge & Autonomous Agent Platform (Phase 6 Active)",
    version="1.0.0",
    debug=settings.debug
)

# Register Global Exception Handlers
app.add_exception_handler(SecurityError, global_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Security & Observability Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimiterMiddleware, requests_per_minute=180)
app.add_middleware(CorrelationIdMiddleware)

# CORS Middleware with safe configuration
allowed_origins = ["*"] if settings.environment == "development" else ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

# Include API routers
app.include_router(health.router)
app.include_router(projects.router)
app.include_router(jobs.router)
app.include_router(intents.router)
app.include_router(artifacts.router)
app.include_router(library.router)
app.include_router(search.router)
app.include_router(conversations.router)
app.include_router(intelligence.router)
app.include_router(agents.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to VidMind API (MVP-1, Phase 4, Phase 5 & Phase 6 Active)",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/health",
        "readiness_url": "/ready"
    }
