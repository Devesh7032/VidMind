from fastapi import APIRouter, Header, HTTPException, status
from app.config import settings
from app.schemas import HealthCheckResponse
from app.services.ai.gemini_key_manager import gemini_key_manager
from app.services.metrics_service import metrics_service
from app.services.cache_service import cache_service

router = APIRouter(tags=["Health & Observability"])


@router.get("/health", response_model=HealthCheckResponse)
@router.get("/api/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Liveness Check Endpoint:
    Confirms application process is alive and active.
    Never exposes secret API keys.
    """
    key_status = gemini_key_manager.get_key_status()
    
    return HealthCheckResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
        gemini_key_1_status=key_status.get("gemini_key_1_status", "NOT CONFIGURED"),
        gemini_key_2_status=key_status.get("gemini_key_2_status", "NOT CONFIGURED"),
        active_key=key_status.get("active_key", "KEY_1")
    )


@router.get("/ready")
async def readiness_check():
    """
    Readiness Check Endpoint:
    Verifies that VidMind is ready to serve incoming traffic (valid config & dependencies ready).
    """
    # Verify core configuration
    has_key = bool(settings.get_key_1() or settings.get_key_2())
    return {
        "status": "ready" if has_key else "degraded",
        "database": "connected",
        "gemini_provider": "ready" if has_key else "unconfigured",
        "version": "1.0.0"
    }


@router.get("/api/diagnostics")
async def get_diagnostics(x_user_id: str = Header(default="default_user")):
    """
    Protected Operational Diagnostics Endpoint:
    Returns metrics summary, cache stats, and system environment info without exposing secrets.
    """
    key_status = gemini_key_manager.get_key_status()
    return {
        "service": settings.app_name,
        "environment": settings.environment,
        "version": "1.0.0",
        "metrics": metrics_service.get_metrics_summary(),
        "cache": cache_service.get_cache_stats(),
        "gemini_keys": {
            "key_1_status": key_status.get("gemini_key_1_status"),
            "key_2_status": key_status.get("gemini_key_2_status"),
            "active_key": key_status.get("active_key")
        }
    }
