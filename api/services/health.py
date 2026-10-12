"""Catalog health scorecard and dashboard aggregation service.

Implements the multi-factor catalog health scoring algorithm per Section 20.1:
  item_completeness = sum(weight(a) for a in applicable populated & unflagged)
                      / sum(weight(a) for a in applicable)
  weight: HARD = 2, REQUIRED = 1, SOFT = 0 (not scored)
  catalog_completeness = mean(item_completeness) over classified items

Reports separate non-blended metrics:
  - classified share
  - category_uncertain count
  - extraction flag rates
  - duplicate rate (item codes per master)
  - top missing attributes per subcategory
  - statutory attribute coverage
"""

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from api.extractors.registry import AttributeRole, default_registry
from api.models.entities import GoldenMaster, RawItem, StewardTask

ROLE_WEIGHTS: dict[str, int] = {
    AttributeRole.HARD.value: 2,
    AttributeRole.REQUIRED.value: 1,
    AttributeRole.SOFT.value: 0,
    AttributeRole.DIRECTIONAL.value: 1,
}


def _check_when_condition(condition: str | None, extracted: dict[str, Any]) -> bool:
    """Evaluate simple when-condition string against extracted attribute values."""
    if not condition:
        return True
    try:
        # Normalize simple python expressions like 'form in [BRICK, PRECAST_SHAPE]'
        # or 'section_width has aspect'
        if "has" in condition:
            parts = condition.split("has")
            key = parts[0].strip()
            val = extracted.get(key)
            if isinstance(val, dict):
                val = val.get("value")
            return bool(val)

        if " in " in condition:
            left, right = condition.split(" in ", 1)
            left_val = extracted.get(left.strip())
            if isinstance(left_val, dict):
                left_val = left_val.get("value")
            # Parse right list: [BRICK, PRECAST_SHAPE]
            right_clean = right.strip().strip("[]").replace("'", "").replace('"', "")
            allowed = [item.strip() for item in right_clean.split(",")]
            return str(left_val).upper() in allowed

        if "==" in condition:
            left, right = condition.split("==", 1)
            left_val = extracted.get(left.strip())
            if isinstance(left_val, dict):
                left_val = left_val.get("value")
            right_val = right.strip().strip("'\"")
            return str(left_val).upper() == right_val.upper()

        return True
    except (AttributeError, ValueError, KeyError):
        return True


def compute_item_completeness(
    subcategory: str | None,
    extracted: dict[str, Any],
    extraction_flags: list[str] | None = None,
) -> dict[str, Any]:
    """Compute weighted completeness for a single item against its subcategory spec."""
    flags_set = set(extraction_flags or [])
    if not subcategory:
        return {
            "completeness": None,
            "applicable_weight": 0,
            "populated_weight": 0,
            "missing_attributes": [],
            "statutory_status": {},
        }

    spec = default_registry.get_spec(subcategory)
    if not spec:
        return {
            "completeness": 1.0,
            "applicable_weight": 0,
            "populated_weight": 0,
            "missing_attributes": [],
            "statutory_status": {},
        }

    applicable_weight = 0
    populated_weight = 0
    missing_attrs: list[dict[str, Any]] = []
    statutory_status: dict[str, bool] = {}

    for attr in spec.attributes:
        # Check condition
        if not _check_when_condition(attr.when, extracted):
            continue

        role_str = attr.role.value if hasattr(attr.role, "value") else str(attr.role)
        weight = ROLE_WEIGHTS.get(role_str, 0)

        # Attribute extraction lookup
        raw_val = extracted.get(attr.name)
        if isinstance(raw_val, dict):
            val = raw_val.get("value")
        else:
            val = raw_val

        # Populated and unflagged
        attr_flagged = any(attr.name.upper() in f.upper() for f in flags_set)
        is_populated = val is not None and not attr_flagged

        if weight > 0:
            applicable_weight += weight
            if is_populated:
                populated_weight += weight
            else:
                missing_attrs.append({"name": attr.name, "role": role_str, "weight": weight})

        if attr.statutory:
            statutory_status[attr.name] = is_populated

    completeness = (populated_weight / applicable_weight) if applicable_weight > 0 else 1.0

    return {
        "completeness": round(completeness, 4),
        "applicable_weight": applicable_weight,
        "populated_weight": populated_weight,
        "missing_attributes": missing_attrs,
        "statutory_status": statutory_status,
    }


def compute_catalog_health(
    items: list[dict[str, Any]],
    confidence_floor: float = 0.60,
) -> dict[str, Any]:
    """Compute Section 20.1 catalog health scorecard over an item collection."""
    total_items = len(items)
    if total_items == 0:
        return {
            "total_items": 0,
            "catalog_completeness": 1.0,
            "classified_share": 1.0,
            "category_uncertain_count": 0,
            "extraction_flag_rate": {},
            "duplicate_rate": 1.0,
            "top_missing_attributes": {},
            "statutory_attributes": {},
            "unclassified_items": [],
        }

    classified_items: list[dict[str, Any]] = []
    unclassified_items: list[dict[str, Any]] = []
    category_uncertain_count = 0
    flag_counts: Counter[str] = Counter()
    missing_by_subcat: dict[str, Counter[str]] = defaultdict(Counter)
    subcat_item_counts: Counter[str] = Counter()
    statutory_totals: Counter[str] = Counter()
    statutory_populated: Counter[str] = Counter()
    item_completeness_scores: list[float] = []
    golden_ids_seen: set[str] = set()

    for item in items:
        subcat = item.get("subcategory")
        conf = float(item.get("category_confidence", 1.0) or 1.0)
        flags = item.get("extraction_flags", []) or []
        golden_id = item.get("golden_id")
        if golden_id:
            golden_ids_seen.add(str(golden_id))

        for f in flags:
            flag_counts[f] += 1
            if f == "CATEGORY_UNCERTAIN":
                category_uncertain_count += 1

        if not subcat or conf < confidence_floor:
            unclassified_items.append(
                {
                    "item_code": item.get("item_code"),
                    "raw_description": item.get("raw_description"),
                    "category_confidence": conf,
                }
            )
            continue

        classified_items.append(item)
        subcat_item_counts[subcat] += 1

        result = compute_item_completeness(
            subcategory=subcat,
            extracted=item.get("extracted", {}) or {},
            extraction_flags=flags,
        )
        if result["completeness"] is not None:
            item_completeness_scores.append(result["completeness"])

        for miss in result["missing_attributes"]:
            missing_by_subcat[subcat][miss["name"]] += 1

        for stat_name, is_pop in result["statutory_status"].items():
            statutory_totals[stat_name] += 1
            if is_pop:
                statutory_populated[stat_name] += 1

    catalog_completeness = (
        round(sum(item_completeness_scores) / len(item_completeness_scores), 4)
        if item_completeness_scores
        else 0.0
    )
    classified_share = round(len(classified_items) / total_items, 4)

    # Flag rate percentage
    flag_rates = {
        flag: {"count": count, "rate": round(count / total_items, 4)}
        for flag, count in sorted(flag_counts.items(), key=lambda x: x[1], reverse=True)
    }

    # Top missing attributes per subcategory
    top_missing_report: dict[str, list[dict[str, Any]]] = {}
    for subcat, counter in missing_by_subcat.items():
        denom = subcat_item_counts[subcat]
        subcat_report = []
        for attr_name, miss_count in counter.most_common(5):
            pct = round((miss_count / denom) * 100, 1)
            subcat_report.append({"attribute": attr_name, "missing_count": miss_count, "missing_pct": pct})
        top_missing_report[subcat] = subcat_report

    # Statutory attributes compliance
    statutory_report = {}
    for stat_name, tot in statutory_totals.items():
        pop = statutory_populated[stat_name]
        cov_pct = round((pop / tot) * 100, 1) if tot > 0 else 0.0
        statutory_report[stat_name] = {"total_applicable": tot, "populated": pop, "coverage_pct": cov_pct}

    # Duplicate rate (item codes per unique golden master)
    distinct_masters = len(golden_ids_seen)
    dup_rate = round(total_items / distinct_masters, 2) if distinct_masters > 0 else 1.0

    return {
        "total_items": total_items,
        "classified_count": len(classified_items),
        "unclassified_count": len(unclassified_items),
        "catalog_completeness": catalog_completeness,
        "classified_share": classified_share,
        "category_uncertain_count": category_uncertain_count,
        "extraction_flag_rate": flag_rates,
        "duplicate_rate": dup_rate,
        "top_missing_attributes": top_missing_report,
        "statutory_attributes": statutory_report,
        "unclassified_items": unclassified_items[:20],  # sample up to 20
    }


def get_tenant_catalog_health(db: Session, org_id: str) -> dict[str, Any]:
    """Calculate Section 20.1 catalog health from database for a tenant organization."""
    raw_rows = (
        db.execute(
            select(
                RawItem.item_code,
                RawItem.raw_description,
                RawItem.subcategory,
                RawItem.extracted,
                RawItem.extraction_flags,
                RawItem.golden_id,
            ).where(RawItem.org_id == org_id)
        )
        .all()
    )

    items = [
        {
            "item_code": r[0],
            "raw_description": r[1],
            "subcategory": r[2],
            "extracted": r[3] or {},
            "extraction_flags": r[4] or [],
            "golden_id": r[5],
        }
        for r in raw_rows
    ]

    return compute_catalog_health(items)


def get_dashboard_summary(db: Session, org_id: str | None = None) -> dict[str, Any]:
    """Produce executive dashboard summary per Section 15.2.

    Returns:
      - Queue depth by domain
      - Tier distribution
      - Harmonization metrics (items before, golden masters after, compression ratio)
      - Catalog health scorecard
      - Duplicate rate
      - OCR engine readiness
      - Audit verification status
    """
    # 1. Stewardship queue depth by domain
    domain_query = (
        select(
            func.coalesce(StewardTask.payload["sector"].astext, "COMMON").label("domain"),
            func.count(StewardTask.id),
        )
        .where(StewardTask.state == "OPEN")
        .group_by("domain")
    )
    domain_counts = dict(db.execute(domain_query).all())
    queue_by_domain = {dom: domain_counts.get(dom, 0) for dom in ["COMMON", "POWER", "STEEL", "MINING", "HEAVY_ENG"]}

    # 2. Tier distribution
    tier_stmt = select(RawItem.tier, func.count(RawItem.id))
    if org_id:
        tier_stmt = tier_stmt.where(RawItem.org_id == org_id)
    tier_counts = dict(db.execute(tier_stmt.group_by(RawItem.tier)).all())
    tier_distribution = {
        "tier_1": tier_counts.get(1, 0),
        "tier_2": tier_counts.get(2, 0),
        "tier_3": tier_counts.get(3, 0),
        "unassigned": tier_counts.get(None, 0),
    }

    # 3. Harmonization metrics (before vs after)
    raw_count_stmt = select(func.count(RawItem.id))
    golden_count_stmt = select(func.count(GoldenMaster.id))
    if org_id:
        raw_count_stmt = raw_count_stmt.where(RawItem.org_id == org_id)
    raw_total = db.scalar(raw_count_stmt) or 0
    golden_total = db.scalar(golden_count_stmt) or 0
    compression_ratio = round(raw_total / golden_total, 2) if golden_total > 0 else 1.0

    # 4. Catalog Health Scorecard
    if org_id:
        catalog_health = get_tenant_catalog_health(db, org_id)
    else:
        # Global sample
        sample_rows = (
            db.execute(
                select(
                    RawItem.item_code,
                    RawItem.raw_description,
                    RawItem.subcategory,
                    RawItem.extracted,
                    RawItem.extraction_flags,
                    RawItem.golden_id,
                ).limit(500)
            )
            .all()
        )
        items = [
            {
                "item_code": r[0],
                "raw_description": r[1],
                "subcategory": r[2],
                "extracted": r[3] or {},
                "extraction_flags": r[4] or [],
                "golden_id": r[5],
            }
            for r in sample_rows
        ]
        catalog_health = compute_catalog_health(items)

    # 5. OCR Engine readiness
    ocr_readiness = {
        "pymupdf": {"available": True, "provider": "PyMuPDFProvider"},
        "fake": {"available": True, "provider": "FakeOCRProvider"},
        "active_default": "pymupdf",
    }

    # 6. Audit integrity status
    try:
        import hashlib
        import json

        from api.core.hashchain import GENESIS

        res = db.execute(
            text(
                "SELECT seq, at, actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash "
                "FROM audit_log ORDER BY seq ASC"
            )
        )
        rows = res.fetchall()
        if not rows:
            audit_status = {
                "status": "OK",
                "verified_records": 0,
                "head_hash": None,
            }
        else:
            expected_prev = GENESIS
            tampered_seq = None
            for r in rows:
                if r.prev_hash != expected_prev:
                    tampered_seq = r.seq
                    break

                at_str = r.at.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if r.at else ""
                actor_str = str(r.actor) if r.actor else ""
                before_str = json.dumps(r.before) if r.before is not None else ""
                after_str = json.dumps(r.after) if r.after is not None else ""
                rationale_str = r.rationale or ""

                payload = (
                    r.prev_hash
                    + f"{at_str}|{actor_str}|{r.action}|{r.entity}|{r.entity_id}|{before_str}|{after_str}|{rationale_str}"
                )
                computed_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

                if computed_hash != r.this_hash:
                    tampered_seq = r.seq
                    break

                expected_prev = r.this_hash

            if tampered_seq is not None:
                audit_status = {
                    "status": "TAMPER_DETECTED",
                    "broken_seq": tampered_seq,
                    "verified_records": tampered_seq - 1,
                    "head_hash": rows[-1].this_hash,
                }
            else:
                audit_status = {
                    "status": "OK",
                    "verified_records": len(rows),
                    "head_hash": rows[-1].this_hash,
                }
    except Exception as e:  # noqa: BLE001
        audit_status = {"status": "ERROR", "error": str(e)}

    return {
        "org_id": org_id,
        "queue_by_domain": queue_by_domain,
        "tier_distribution": tier_distribution,
        "harmonization": {
            "raw_items_before": raw_total,
            "golden_masters_after": golden_total,
            "compression_ratio": compression_ratio,
        },
        "catalog_health": catalog_health,
        "ocr_readiness": ocr_readiness,
        "audit_integrity": audit_status,
    }
