"""Prometheus metrics endpoint.

Exposes GET /metrics in standard Prometheus format per Section 15.2.
Guarantees zero leakage of tenant, user, or item identifiers.
"""

from fastapi import APIRouter, Response

from api.database import SyncSessionLocal
from api.services.observability import collect_live_database_gauges, metrics_registry

router = APIRouter(tags=["observability"])


@router.get("/metrics", response_class=Response)
def get_prometheus_metrics() -> Response:
    """Expose system metrics in standard Prometheus exposition format."""
    with SyncSessionLocal() as db:
        collect_live_database_gauges(db)
    content = metrics_registry.render_text()
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")

