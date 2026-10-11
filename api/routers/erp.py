"""ERP Interoperability and Export Endpoints per Section 12.0.

Exposes REST endpoint:
  - GET /erp/export?target=&format=&feed=
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse

from api.config import get_settings
from api.database import SyncSessionLocal
from api.models.entities import Organization
from api.security.jwt_auth import AuthUser, get_current_user
from api.services.erp import (
    generate_erp_export_payload,
    serialize_to_csv,
    serialize_to_xlsx,
)

router = APIRouter(prefix="/erp", tags=["erp"])


def _parse_uuid(val: Any) -> uuid.UUID | None:
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError, AttributeError):
        return None


@router.get("/export")
def export_erp_feed(
    target: str | None = Query(None, description="Target ERP system: sap, oracle, or maximo"),
    format: str = Query("json", description="Export format: json, csv, or xlsx"),
    feed: str = Query("items", description="Feed selection for CSV: items, classifications, or all"),
    user: AuthUser = Depends(get_current_user),
) -> Response:
    """Exports material catalogue cross-reference and classification feeds for host ERP systems."""
    settings = get_settings()

    with SyncSessionLocal() as db:
        # Resolve target from query, org profile, or app settings
        if not target:
            org = db.query(Organization).filter(Organization.id == user.org_id).first()
            if org and org.profile and org.profile.get("erp_target"):
                target = str(org.profile["erp_target"])
            else:
                target = settings.erp_target

        payload = generate_erp_export_payload(
            db=db,
            org_id=user.org_id,
            target=target,
            user_id=_parse_uuid(user.sub),
        )
        db.commit()

    fmt_lower = format.strip().lower()

    if fmt_lower == "xlsx":
        xlsx_bytes = serialize_to_xlsx(payload)
        filename = f"{target}_catalog_{user.org_id}.xlsx"
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if fmt_lower == "csv":
        feed_choice = feed.strip().lower()
        if feed_choice == "classifications":
            csv_text = serialize_to_csv(payload.get("classifications", []))
            filename = f"{target}_classifications_{user.org_id}.csv"
        else:
            csv_text = serialize_to_csv(payload.get("items", []))
            filename = f"{target}_items_{user.org_id}.csv"

        return Response(
            content=csv_text,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Default: JSON format
    return JSONResponse(content=payload)
