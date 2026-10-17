"""Inter-CPSE Spare Locator router per Section 12.0 and 13.2.

Exposes REST endpoints for geographic spare location and inventory availability queries:
  - GET /locator
  - GET /availability
"""

from typing import Any

from fastapi import APIRouter, Depends, Query

from api.database import tenant_sync_session
from api.security.jwt_auth import AuthUser, get_current_user
from api.services.locator import search_spare_locator

router = APIRouter(tags=["locator"])


@router.get("/locator")
def get_spare_locator(
    query_text: str | None = Query(None, description="Search term for Golden Master descriptor or code"),
    golden_id: str | None = Query(None, description="Exact Golden Master UUID"),
    requester_plant_code: str | None = Query(None, description="Origin plant code of current CPSE"),
    max_distance_km: float | None = Query(None, description="Maximum air distance radius in km"),
    min_idle_days: int = Query(0, description="Minimum inventory idle days"),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Search for spare inventory across all CPSE plants with distance calculation and privacy masking."""
    with tenant_sync_session(user.org_id) as db:
        return search_spare_locator(
            db=db,
            current_org_id=user.org_id,
            query_text=query_text,
            golden_id=golden_id,
            requester_plant_code=requester_plant_code,
            max_distance_km=max_distance_km,
            min_idle_days=min_idle_days,
        )


@router.get("/availability")
def get_surplus_availability(
    golden_id: str | None = Query(None, description="Golden Master UUID"),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Check Tier 1 surplus availability across partner CPSEs for a specific Golden Master."""
    with tenant_sync_session(user.org_id) as db:
        res = search_spare_locator(
            db=db,
            current_org_id=user.org_id,
            golden_id=golden_id,
        )
        # Filter for external partner surplus only
        surplus_only = [item for item in res["results"] if not item["is_own_inventory"]]
        return {
            "golden_id": golden_id,
            "total_surplus_locations": len(surplus_only),
            "available_items": surplus_only,
        }
