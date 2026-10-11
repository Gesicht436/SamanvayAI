"""Health and diagnostic endpoint."""

from fastapi import APIRouter

from api.config import get_settings

router = APIRouter(prefix="", tags=["Health"])


@router.get("/health")
async def health_check():
    """Return system readiness, configuration status, and runtime mode."""
    settings = get_settings()
    return {
        "status": "OK",
        "service": "Samanvay Material Harmonization API",
        "clock_mode": settings.clock_mode,
        "demo_mode": settings.demo_mode,
        "ml_layer": settings.ml_layer,
    }
