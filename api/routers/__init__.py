"""FastAPI API routers package for Samanvay."""

from api.routers.audit import router as audit_router
from api.routers.auth import router as auth_router
from api.routers.compare import router as compare_router
from api.routers.extract import router as extract_router
from api.routers.health import router as health_router
from api.routers.ingest import router as ingest_router
from api.routers.match import router as match_router
from api.routers.tasks import router as tasks_router

__all__ = [
    "audit_router",
    "auth_router",
    "compare_router",
    "extract_router",
    "health_router",
    "ingest_router",
    "match_router",
    "tasks_router",
]
