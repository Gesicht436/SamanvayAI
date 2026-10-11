"""OEM catalogue onboarding wizard service.

Implements bulk catalogue onboarding for proprietary and OEM-keyed families
per Section 20.2:
  1. Maker uploads OEM catalogue (CSV, XLSX, JSON).
  2. Extracts OEM, part number, drawing number, parent equipment model, description.
  3. Applies supersession table (oem_part_supersessions).
  4. Proposes DRAFT masters with identity_mode = OEM_PN.
  5. Maker reviews proposals with evidence spans.
  6. Checker with domain tag approves (Maker != Checker enforced).
  7. Publishes masters and registers aliases with transactional audit logging.
"""

import hashlib
import re
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.entities import (
    GoldenAlias,
    GoldenMaster,
    OemCatalogueBatch,
    OemPartSupersession,
    OemProposal,
)
from api.services.audit import append_audit_entry
from api.services.lifecycle import generate_unique_mpng_code


def normalize_oem_part_number(pn: str) -> str:
    """Normalize OEM part number: uppercase and strip punctuation / whitespace."""
    if not pn:
        return ""
    return re.sub(r"[\s\-_/.]+", "", pn).strip().upper()


def normalize_oem_name(name: str) -> str:
    """Normalize manufacturer / OEM name."""
    if not name:
        return ""
    return re.sub(r"\s+", " ", name).strip().upper()


def extract_evidence_span(text: str, target: str) -> list[int]:
    """Find character offset [start, end] of target substring in raw text."""
    if not text or not target:
        return [0, 0]
    idx = text.upper().find(target.upper())
    if idx != -1:
        return [idx, idx + len(target)]
    return [0, 0]


def lookup_supersession(db: Session, manufacturer: str, norm_pn: str) -> tuple[str, str | None, str | None]:
    """Check if part number is superseded. Returns (effective_pn, superseded_from, note)."""
    mfr_norm = normalize_oem_name(manufacturer)
    row = db.execute(
        select(OemPartSupersession).where(
            OemPartSupersession.manufacturer == mfr_norm,
            OemPartSupersession.old_pn == norm_pn,
        )
    ).scalar_one_or_none()

    if row:
        return row.new_pn, norm_pn, row.note
    return norm_pn, None, None


def ingest_oem_catalogue_rows(
    db: Session,
    org_id: str,
    oem_name: str,
    filename: str,
    rows: list[dict[str, Any]],
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Ingest rows from an OEM catalogue file and generate draft proposals."""
    norm_mfr = normalize_oem_name(oem_name)
    content_bytes = f"{norm_mfr}:{filename}:{len(rows)}".encode()
    file_hash = hashlib.sha256(content_bytes).hexdigest()

    batch = OemCatalogueBatch(
        org_id=org_id,
        oem_name=norm_mfr,
        filename=filename,
        file_hash=file_hash,
        total_rows=len(rows),
        status="PROPOSED",
        created_by=user_id,
        summary={"rows_count": len(rows)},
    )
    db.add(batch)
    db.flush()

    proposals: list[OemProposal] = []
    superseded_count = 0

    for r in rows:
        raw_pn = str(r.get("part_number") or r.get("pn") or r.get("item_code") or "").strip()
        raw_desc = str(r.get("description") or r.get("desc") or raw_pn).strip()
        drawing_no = str(r.get("drawing_no") or r.get("drawing") or "").strip() or None
        parent_model = str(r.get("parent_equipment_model") or r.get("model") or "").strip() or None
        subcategory = str(r.get("subcategory") or "HEAVY.PUMP_SPARE").strip()

        norm_pn = normalize_oem_part_number(raw_pn)
        effective_pn, superseded_from, _ = lookup_supersession(db, norm_mfr, norm_pn)
        if superseded_from:
            superseded_count += 1

        # Evidence spans
        spans = {
            "oem": extract_evidence_span(raw_desc, norm_mfr),
            "part_number": extract_evidence_span(raw_desc, raw_pn),
        }
        if drawing_no:
            spans["drawing_no"] = extract_evidence_span(raw_desc, drawing_no)

        proposal = OemProposal(
            batch_id=batch.id,
            org_id=org_id,
            oem_name=norm_mfr,
            raw_part_number=raw_pn,
            norm_part_number=norm_pn,
            effective_part_number=effective_pn,
            superseded_from=superseded_from,
            drawing_no=drawing_no,
            parent_equipment_model=parent_model,
            raw_description=raw_desc,
            subcategory=subcategory,
            evidence_spans=spans,
            status="PROPOSED",
        )
        proposals.append(proposal)
        db.add(proposal)

    db.flush()

    # Log audit entry
    append_audit_entry(
        db=db,
        actor=user_id,
        action="OEM_CATALOGUE_UPLOAD",
        entity_type="oem_catalogue_batches",
        entity_id=str(batch.id),
        old_val=None,
        new_val={"batch_id": str(batch.id), "total_rows": len(rows), "superseded_count": superseded_count},
    )

    batch.summary = {
        "rows_count": len(rows),
        "proposals_count": len(proposals),
        "superseded_count": superseded_count,
    }
    db.commit()

    return {
        "batch_id": str(batch.id),
        "status": batch.status,
        "total_rows": len(rows),
        "superseded_count": superseded_count,
    }


def review_proposal(
    db: Session,
    proposal_id: int,
    action: str,  # ACCEPT, REJECT, EDIT
    edited_part_number: str | None = None,
    edited_description: str | None = None,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Maker review of a single proposal in bulk onboarding."""
    prop = db.get(OemProposal, proposal_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Proposal not found")

    old_status = prop.status
    if action == "ACCEPT":
        prop.status = "ACCEPTED"
    elif action == "REJECT":
        prop.status = "REJECTED"
    elif action == "EDIT":
        if edited_part_number:
            prop.effective_part_number = normalize_oem_part_number(edited_part_number)
        if edited_description:
            prop.raw_description = edited_description
        prop.status = "ACCEPTED"

    prop.reviewed_by = user_id
    db.flush()

    append_audit_entry(
        db=db,
        actor=user_id,
        action="OEM_PROPOSAL_REVIEW",
        entity_type="oem_proposals",
        entity_id=str(prop.id),
        old_val={"status": old_status},
        new_val={"status": prop.status, "action": action},
    )
    db.commit()

    return {
        "proposal_id": prop.id,
        "status": prop.status,
        "effective_part_number": prop.effective_part_number,
    }


def approve_catalogue_batch(
    db: Session,
    batch_id: uuid.UUID,
    checker_id: uuid.UUID,
    user_roles: list[str],
    user_domain_tags: list[str],
    rationale: str,
) -> dict[str, Any]:
    """Checker approves the OEM catalogue batch.

    Enforces:
      - Maker-Checker: checker != batch.created_by
      - Domain tag match (e.g. 'HEAVY_ENG' or 'COMMON')
      - Publishes active golden masters with identity_mode = OEM_PN
      - Registers golden aliases
      - Writes audit log in the exact same database transaction!
    """
    batch = db.get(OemCatalogueBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Catalogue batch not found")

    # Invariant: Maker != Checker
    if batch.created_by and str(batch.created_by) == str(checker_id):
        raise HTTPException(
            status_code=403,
            detail={"code": "MAKER_CHECKER_VIOLATION", "message": "The approver must differ from the proposer."},
        )

    # Domain tag check
    # Check if user has required segment
    if "ADMIN" not in user_roles and not (
        "COMMON" in user_domain_tags or "HEAVY_ENG" in user_domain_tags or "MINING" in user_domain_tags
    ):
        raise HTTPException(
            status_code=403,
            detail={"code": "DOMAIN_TAG_REQUIRED", "message": "Approval needs the domain tag for OEM equipment."},
        )

    proposals = (
        db.execute(
            select(OemProposal).where(
                OemProposal.batch_id == batch_id,
                OemProposal.status.in_(["PROPOSED", "ACCEPTED"]),
            )
        )
        .scalars()
        .all()
    )

    published_masters: list[str] = []

    for prop in proposals:
        # Descriptor format: SUB.CAT | OEM | PART_NO | DESC
        descriptor = f"{prop.subcategory or 'OEM_PART'} | {prop.oem_name} | {prop.effective_part_number}"
        golden_code = generate_unique_mpng_code()

        major_cat = prop.subcategory.split(".")[0] if prop.subcategory else "HEAVY"
        master = GoldenMaster(
            code=golden_code,
            descriptor=descriptor,
            status="ACTIVE",
            major_category=major_cat,
            subcategory=prop.subcategory or "OEM_PART",
            block_key=prop.effective_part_number[:10],
            identity_mode="OEM_PN",
            is_proprietary=True,
            oem_name_norm=prop.oem_name,
            oem_part_number_norm=prop.effective_part_number,
            canonical_text=f"{prop.oem_name} {prop.effective_part_number}",
            canonical_uom="EA",
            attributes={
                "oem": prop.oem_name,
                "part_number": prop.effective_part_number,
                "drawing_no": prop.drawing_no,
                "parent_equipment_model": prop.parent_equipment_model,
            },
        )
        db.add(master)
        db.flush()

        prop.golden_id = master.id
        prop.status = "APPROVED"
        published_masters.append(golden_code)

        # Register Alias for effective part number
        existing_alias = db.execute(
            select(GoldenAlias).where(
                GoldenAlias.alias_type == "OEM_PART_NO",
                GoldenAlias.org_id == batch.org_id,
                GoldenAlias.value_norm == prop.effective_part_number,
            )
        ).scalar_one_or_none()
        if existing_alias:
            existing_alias.golden_id = master.id
            existing_alias.value_raw = prop.raw_part_number
        else:
            alias = GoldenAlias(
                golden_id=master.id,
                alias_type="OEM_PART_NO",
                org_id=batch.org_id,
                value_raw=prop.raw_part_number,
                value_norm=prop.effective_part_number,
            )
            db.add(alias)

        # If superseded, register alias for superseded part number too
        if prop.superseded_from:
            existing_super = db.execute(
                select(GoldenAlias).where(
                    GoldenAlias.alias_type == "SUPERSEDED_PART_NO",
                    GoldenAlias.org_id == batch.org_id,
                    GoldenAlias.value_norm == prop.superseded_from,
                )
            ).scalar_one_or_none()
            if existing_super:
                existing_super.golden_id = master.id
                existing_super.value_raw = prop.superseded_from
            else:
                alias_super = GoldenAlias(
                    golden_id=master.id,
                    alias_type="SUPERSEDED_PART_NO",
                    org_id=batch.org_id,
                    value_raw=prop.superseded_from,
                    value_norm=prop.superseded_from,
                )
                db.add(alias_super)

    batch.status = "COMPLETED"
    db.flush()

    audit_entry = append_audit_entry(
        db=db,
        actor=checker_id,
        action="OEM_CATALOGUE_APPROVE",
        entity_type="oem_catalogue_batches",
        entity_id=str(batch.id),
        old_val={"status": "PROPOSED"},
        new_val={
            "status": "COMPLETED",
            "published_count": len(published_masters),
            "rationale": rationale,
            "published_codes": published_masters[:10],
        },
    )
    db.commit()

    return {
        "batch_id": str(batch.id),
        "status": "COMPLETED",
        "published_masters_count": len(published_masters),
        "audit_seq": audit_entry.seq,
        "audit_hash": audit_entry.hash,
    }
