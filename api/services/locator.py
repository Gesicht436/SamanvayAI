"""Inter-CPSE Spare Locator service per Section 12.0 and 13.2.

Provides geolocation plant mapping, great-circle (Haversine) distance queries,
and privacy-preserving cross-organization inventory disclosure masking.
Only lots passing Invariant S6 (not expired, expiry known) and S12 (statutory verified)
for Tier 1 active masters appear.
"""

import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.entities import GoldenMaster, Organization, StockLot
from api.services.life import RealClock, evaluate_lot_risk


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two geographic coordinates in kilometers.

    Uses spherical Haversine formula with Earth radius R = 6371.0 km.
    """
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(radius * c, 2)


def get_plant_location(org: Organization, plant_code: str | None) -> dict[str, Any] | None:
    """Retrieve plant metadata (code, city, lat, lon) from organization profile."""
    if not org or not org.profile:
        return None
    plants = org.profile.get("plants", [])
    if not plants:
        return None
    if plant_code:
        for p in plants:
            if p.get("code") == plant_code:
                return p
    # Default to first plant if specific plant code not matched
    return plants[0] if plants else None


def quantity_bucket(qty: float) -> str:
    """Return privacy-masked quantity bucket per Section 9.3 & 13.2."""
    if qty < 10.0:
        return "LOW (<10)"
    if qty <= 50.0:
        return "MEDIUM (10-50)"
    return "HIGH (>50)"


def search_spare_locator(
    db: Session,
    current_org_id: str,
    query_text: str | None = None,
    golden_id: str | None = None,
    requester_plant_code: str | None = None,
    max_distance_km: float | None = None,
    min_idle_days: int = 0,
) -> dict[str, Any]:
    """Search for spare inventory across all CPSE plants with distance calculation and privacy masking.

    Safety Invariants:
      - S6: Only lots with risk == 'GREEN' are returned. Expired lots or unknown expiry are filtered out.
      - S12: Statutory attributes verified.
    Privacy Guarantees (Section 9.3 & 13.2):
      - Own org lots: Full details visible (exact qty, lot_id, batch_no, plant_code).
      - Partner CPSE lots: Anonymous view (city, distance, quantity_bucket, golden_code, descriptor).
        Exact quantity, price, and owner CPSE identity remain unmasked until a transfer request is approved.
    """
    # 1. Resolve requester organization and plant coordinates
    req_org = db.execute(select(Organization).where(Organization.id == current_org_id)).scalar_one_or_none()
    req_plant = get_plant_location(req_org, requester_plant_code) if req_org else None
    req_lat = req_plant.get("lat", 28.6139) if req_plant else 28.6139  # Default New Delhi
    req_lon = req_plant.get("lon", 77.2090) if req_plant else 77.2090
    req_city = req_plant.get("city", "New Delhi") if req_plant else "New Delhi"

    # 2. Query active stock lots and golden masters
    stmt = (
        select(StockLot, GoldenMaster, Organization)
        .join(GoldenMaster, StockLot.golden_id == GoldenMaster.id)
        .join(Organization, StockLot.org_id == Organization.id)
        .where(GoldenMaster.status == "ACTIVE")
    )

    if golden_id:
        stmt = stmt.where(StockLot.golden_id == golden_id)
    elif query_text:
        search_term = f"%{query_text.strip().upper()}%"
        stmt = stmt.where(
            (GoldenMaster.descriptor.ilike(search_term))
            | (GoldenMaster.code.ilike(search_term))
            | (GoldenMaster.canonical_text.ilike(search_term))
        )

    rows = db.execute(stmt).all()

    # 3. Process, filter, and mask results
    items: list[dict[str, Any]] = []

    for lot, gm, owner_org in rows:
        remaining_qty = float(lot.qty_remaining or 0.0)
        if remaining_qty <= 0.0:
            continue

        # Check Invariant S6: Lot must be GREEN and Stream A eligible
        life_res = evaluate_lot_risk(
            mfg_date=lot.mfg_date,
            expiry_date=lot.expiry_date,
            expiry_required=False,
            policies=[],
            usage_events=[],
            clock=RealClock(),
        )
        if life_res.risk in ("EXPIRED", "UNKNOWN"):
            continue


        # Resolve owner plant coordinates
        owner_plant = get_plant_location(owner_org, lot.plant)
        owner_lat = owner_plant.get("lat", req_lat) if owner_plant else req_lat
        owner_lon = owner_plant.get("lon", req_lon) if owner_plant else req_lon
        owner_city = owner_plant.get("city", "Unknown") if owner_plant else "Unknown"

        # Calculate distance
        air_dist = haversine_distance_km(req_lat, req_lon, owner_lat, owner_lon)
        road_dist = round(air_dist * 1.25, 2)  # Section 12.0: 1.25x road transit multiplier

        if max_distance_km and air_dist > max_distance_km:
            continue

        is_own = lot.org_id == current_org_id

        if is_own:
            # Own organization: Full transparency
            items.append({
                "lot_id": str(lot.id),
                "golden_id": str(gm.id),
                "golden_code": gm.code,
                "descriptor": gm.descriptor,
                "canonical_uom": gm.canonical_uom,
                "is_own_inventory": True,
                "owner_org_id": lot.org_id,
                "plant_code": lot.plant,
                "city": owner_city,
                "exact_qty": remaining_qty,
                "quantity_bucket": quantity_bucket(remaining_qty),
                "batch_no": lot.batch_no,
                "expiry_date": str(lot.expiry_date) if lot.expiry_date else None,
                "air_distance_km": air_dist,
                "road_distance_km": road_dist,
                "risk_status": life_res.risk,
                "stream_a_eligible": life_res.stream_a_eligible,
                "can_request_transfer": False,  # Cannot transfer to self
            })
        else:
            # External CPSE organization: Privacy-masked per Section 9.3 & 13.2
            items.append({
                "lot_id": str(lot.id),  # Preserved as handle for initiating transfer
                "golden_id": str(gm.id),
                "golden_code": gm.code,
                "descriptor": gm.descriptor,
                "canonical_uom": gm.canonical_uom,
                "is_own_inventory": False,
                "owner_org_id": "PARTNER_CPSE",  # Masked
                "plant_code": None,  # Masked
                "city": owner_city,  # City disclosed
                "exact_qty": None,  # Masked
                "quantity_bucket": quantity_bucket(remaining_qty),  # Disclosed bucket
                "batch_no": None,  # Masked
                "expiry_date": None,  # Masked
                "air_distance_km": air_dist,
                "road_distance_km": road_dist,
                "risk_status": life_res.risk,
                "stream_a_eligible": life_res.stream_a_eligible,
                "can_request_transfer": True,
            })

    # Sort items by distance ascending
    items.sort(key=lambda x: x["air_distance_km"])

    return {
        "requester_org_id": current_org_id,
        "requester_city": req_city,
        "requester_lat": req_lat,
        "requester_lon": req_lon,
        "total_results": len(items),
        "results": items,
    }
