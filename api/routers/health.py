"""Health and diagnostic endpoint."""

from fastapi import APIRouter

router = APIRouter(prefix="", tags=["Health"])


@router.get("/health")
async def health_check():
    """Return the basic service health status without revealing runtime configuration."""
    return {
        "status": "OK",
        "service": "Samanvay Material Harmonization API",
    }
