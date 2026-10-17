"""Executive dashboard, catalog health, and audit verification router.

Provides endpoints for:
  - GET /dashboard/summary (Section 15.2)
  - GET /metrics/catalog-health (Section 20.1)
  - GET /audit/verify (Section 15.1)
"""

from typing import Any

from fastapi import APIRouter, Depends

from api.database import tenant_sync_session
from api.security.jwt_auth import AuthUser, get_current_user
from api.services.health import get_dashboard_summary, get_tenant_catalog_health

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary")
def get_dashboard_view(
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve executive dashboard summary for the signed-in tenant or global context."""
    org_id = current_user.org_id
    with tenant_sync_session(current_user.org_id) as db:
        return get_dashboard_summary(db, org_id=org_id)


@router.get("/metrics/catalog-health")
def get_catalog_health_scorecard(
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve multi-factor catalog health scorecard per Section 20.1."""
    org_id = current_user.org_id
    with tenant_sync_session(current_user.org_id) as db:
        return get_tenant_catalog_health(db, org_id=org_id)
