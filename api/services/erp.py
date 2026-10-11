"""ERP Interoperability and Export Adapters per Section 12.0.

Produces cross-reference and classification feeds for host enterprise ERP systems:
- SAP (MARA/MAKT short-text clipped to 40 chars MAKTX, BISMT carrying 17-char MPNG- code).
- Oracle Cloud ERP (Item description clipped to 60 chars, CROSS_REFERENCE carrying national code).
- IBM Maximo (Item description clipped to 50 chars, EXTERNAL_REF carrying national code).

Field lengths resolve dynamically from Organization.profile["field_lengths"] with target defaults.
Never hardcoded. Clean truncation avoids splitting words mid-token.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from typing import Any

import openpyxl
from sqlalchemy.orm import Session

from api.models.entities import GoldenAlias, GoldenMaster, Organization, RawItem
from api.services.audit import append_audit_entry

# VERIFY: SAP ECC/S4 MARA/MAKT default field lengths (MAKTX 40, MATNR 18, BISMT 18) - docs/verification.md VERIFY-012
SAP_DEFAULTS: dict[str, int] = {"description": 40, "code": 18, "cross_ref": 18}

# VERIFY: Oracle Cloud ERP default field lengths (DESCRIPTION 60, ITEM_NUMBER 20) - docs/verification.md VERIFY-013
ORACLE_DEFAULTS: dict[str, int] = {"description": 60, "code": 20, "cross_ref": 30}

# VERIFY: IBM Maximo default field lengths (DESCRIPTION 50, ITEMNUM 16) - docs/verification.md VERIFY-014
MAXIMO_DEFAULTS: dict[str, int] = {"description": 50, "code": 16, "cross_ref": 30}

TARGET_DEFAULTS: dict[str, dict[str, int]] = {
    "sap": SAP_DEFAULTS,
    "oracle": ORACLE_DEFAULTS,
    "maximo": MAXIMO_DEFAULTS,
}


def truncate_clean(text: str, max_len: int) -> str:
    """Safely truncates material descriptor to fit ERP target field length.

    Rules:
    - Never truncates mid-word if a previous word boundary exists at >= 50% length.
    - Strips dangling trailing whitespace and punctuation characters.
    """
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_len:
        return text

    clipped = text[:max_len]
    last_space = clipped.rfind(" ")
    if last_space > 0 and last_space >= max_len // 2:
        clipped = clipped[:last_space]

    clipped = clipped.rstrip(" ,-/:|;.")
    return clipped


def resolve_field_lengths(org_profile: dict[str, Any] | None, target: str) -> dict[str, int]:
    """Resolves target field lengths from per-organization configuration with target defaults.

    Never hard-coded. Defaults are verified citations.
    """
    target_key = (target or "sap").strip().lower()
    defaults = TARGET_DEFAULTS.get(target_key, SAP_DEFAULTS).copy()

    if org_profile and isinstance(org_profile, dict):
        configured = org_profile.get("field_lengths")
        if isinstance(configured, dict):
            for k, v in configured.items():
                if isinstance(v, int) and v > 0:
                    defaults[k] = v

    return defaults


def generate_erp_export_payload(
    db: Session,
    org_id: str,
    target: str = "sap",
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Generates structured ERP export rows for Item Master and Classifications."""
    target_key = (target or "sap").strip().lower()
    if target_key not in TARGET_DEFAULTS:
        target_key = "sap"

    # 1. Fetch organization profile
    org = db.query(Organization).filter(Organization.id == org_id).first()
    org_profile = org.profile if org and org.profile else {}
    field_lengths = resolve_field_lengths(org_profile, target_key)
    desc_max_len = field_lengths.get("description", 40)
    code_max_len = field_lengths.get("code", 18)

    # 2. Query harmonized items for this organization
    # First, collect raw items mapped to golden masters
    raw_items = (
        db.query(RawItem)
        .filter(RawItem.org_id == org_id, RawItem.golden_id.isnot(None))
        .all()
    )

    # Also collect all active golden masters (with any org alias)
    active_goldens = (
        db.query(GoldenMaster)
        .filter(GoldenMaster.status.in_(["ACTIVE", "DRAFT"]))
        .order_by(GoldenMaster.code)
        .all()
    )

    # Cache org aliases
    aliases = (
        db.query(GoldenAlias)
        .filter(GoldenAlias.org_id == org_id, GoldenAlias.alias_type == "CPSE_ITEM_CODE")
        .all()
    )
    alias_by_golden: dict[uuid.UUID, str] = {a.golden_id: a.value_raw for a in aliases}
    raw_code_by_golden: dict[uuid.UUID, str] = {r.golden_id: r.item_code for r in raw_items if r.golden_id and r.item_code}

    items_rows: list[dict[str, Any]] = []
    class_rows: list[dict[str, Any]] = []
    seen_golden_ids: set[uuid.UUID] = set()

    for gm in active_goldens:
        if gm.id in seen_golden_ids:
            continue
        seen_golden_ids.add(gm.id)

        # Determine host ERP item number
        host_code = alias_by_golden.get(gm.id) or raw_code_by_golden.get(gm.id)
        if not host_code:
            # Fallback to sanitized prefix of national code
            host_code = gm.code.replace("MPNG-", "")

        host_code_clipped = truncate_clean(host_code, code_max_len)
        short_desc = truncate_clean(gm.descriptor, desc_max_len)
        national_code = gm.code
        uom = gm.canonical_uom or "EA"
        subcategory = gm.subcategory or "GENERAL"
        clean_class = subcategory.replace(".", "_")

        # 3. Format per target ERP
        if target_key == "sap":
            items_rows.append({
                "MATNR": host_code_clipped,
                "MAKTX": short_desc,
                "BISMT": national_code,  # Old material number / national 17-char code
                "MEINS": uom,
                "MATKL": subcategory,
                "UNSPSC": gm.unspsc_code or "",
                "SPRAS": "EN",
            })
            for attr_k, attr_v in (gm.attributes or {}).items():
                if attr_v is not None and str(attr_v).strip():
                    class_rows.append({
                        "OBJEK": host_code_clipped,
                        "KLART": "001",
                        "CLASS": clean_class,
                        "CHARACT": attr_k.upper(),
                        "VALUE": str(attr_v),
                        "UOM": "",
                    })
        elif target_key == "oracle":
            items_rows.append({
                "ITEM_NUMBER": host_code_clipped,
                "DESCRIPTION": short_desc,
                "CROSS_REFERENCE": national_code,
                "CROSS_REFERENCE_TYPE": "NATIONAL_MATERIAL_CODE",
                "PRIMARY_UOM": uom,
                "ITEM_CATEGORY": subcategory,
                "UNSPSC": gm.unspsc_code or "",
            })
            for attr_k, attr_v in (gm.attributes or {}).items():
                if attr_v is not None and str(attr_v).strip():
                    class_rows.append({
                        "ITEM_NUMBER": host_code_clipped,
                        "CATEGORY_CODE": subcategory,
                        "ATTRIBUTE_GROUP": "TECHNICAL_SPECS",
                        "ATTRIBUTE_NAME": attr_k.upper(),
                        "ATTRIBUTE_VALUE": str(attr_v),
                        "UOM": "",
                    })
        elif target_key == "maximo":
            items_rows.append({
                "ITEMNUM": host_code_clipped,
                "DESCRIPTION": short_desc,
                "EXTERNAL_REF": national_code,
                "ORDERUNIT": uom,
                "ISSUEUNIT": uom,
                "COMMODITY": subcategory,
                "UNSPSC": gm.unspsc_code or "",
            })
            for attr_k, attr_v in (gm.attributes or {}).items():
                if attr_v is not None and str(attr_v).strip():
                    class_rows.append({
                        "ITEMNUM": host_code_clipped,
                        "CLASSIFICATIONID": clean_class,
                        "SECTION": "TECHNICAL_ATTRIBUTES",
                        "PROPNAME": attr_k.upper(),
                        "PROPVALUE": str(attr_v),
                        "MEASUREUNITID": "",
                    })

    # Record transactional audit entry
    append_audit_entry(
        db=db,
        actor=user_id,
        action="ERP_FEED_EXPORTED",
        entity_type="organizations",
        entity_id=org_id,
        old_val=None,
        new_val={
            "target": target_key,
            "field_lengths": field_lengths,
            "items_count": len(items_rows),
            "classifications_count": len(class_rows),
        },
        rationale=f"Generated ERP cross-reference export for target {target_key}",
    )
    db.flush()

    return {
        "target": target_key,
        "org_id": org_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "field_lengths": field_lengths,
        "counts": {
            "items": len(items_rows),
            "classifications": len(class_rows),
        },
        "items": items_rows,
        "classifications": class_rows,
    }


def serialize_to_csv(rows: list[dict[str, Any]]) -> str:
    """Serializes a list of dictionaries to RFC 4180 CSV string."""
    if not rows:
        return ""
    output = io.StringIO()
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def serialize_to_xlsx(payload: dict[str, Any]) -> bytes:
    """Generates a multi-sheet Microsoft Excel (.xlsx) workbook for ERP import."""
    wb = openpyxl.Workbook()

    # Sheet 1: Item Master
    ws_items = wb.active
    ws_items.title = "Item_Master"
    items = payload.get("items", [])
    if items:
        headers = list(items[0].keys())
        ws_items.append(headers)
        for row in items:
            ws_items.append([row.get(h, "") for h in headers])
    else:
        ws_items.append(["No Items Found"])

    # Sheet 2: Classifications
    ws_class = wb.create_sheet(title="Classifications")
    classifications = payload.get("classifications", [])
    if classifications:
        headers = list(classifications[0].keys())
        ws_class.append(headers)
        for row in classifications:
            ws_class.append([row.get(h, "") for h in headers])
    else:
        ws_class.append(["No Classifications Found"])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
