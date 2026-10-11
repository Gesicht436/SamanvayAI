"""FastAPI API routers package for Samanvay."""

from api.routers.audit import router as audit_router
from api.routers.auth import router as auth_router
from api.routers.compare import router as compare_router
from api.routers.dashboard import router as dashboard_router
from api.routers.docs import router as docs_router
from api.routers.extract import router as extract_router
from api.routers.health import router as health_router
from api.routers.ingest import router as ingest_router
from api.routers.locator import router as locator_router
from api.routers.lots import router as lots_router
from api.routers.match import router as match_router
from api.routers.metrics import router as metrics_router
from api.routers.oem import router as oem_router
from api.routers.pools import router as pools_router
from api.routers.tasks import router as tasks_router
from api.routers.transfers import router as transfers_router

__all__ = [
    "audit_router",
    "auth_router",
    "compare_router",
    "dashboard_router",
    "docs_router",
    "extract_router",
    "health_router",
    "ingest_router",
    "locator_router",
    "lots_router",
    "match_router",
    "metrics_router",
    "oem_router",
    "pools_router",
    "tasks_router",
    "transfers_router",
]


