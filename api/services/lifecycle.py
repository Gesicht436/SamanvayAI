"""Golden Master Lifecycle Service.

Implements the Golden Master Lifecycle per Section 8.0:
- States: DRAFT -> ACTIVE -> DEPRECATED
- Terminal actions: MERGED_INTO and SPLIT_INTO
- Code immutability: MPNG- 17-char Verhoeff code never changes
- Transactional audit logging on every state change
"""

from __future__ import annotations

import json
import random
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from api.core.verhoeff import make_code
from api.extractors.registry import default_registry
from api.models.entities import GoldenAlias, GoldenMaster, RawItem
from api.services.candidates import compute_block_key
from api.services.classify import SUBCATEGORY_MAP


class LifecycleError(Exception):
    """Raised when an invalid lifecycle state transition or operation occurs."""


def generate_descriptor(subcategory: str, attributes: dict[str, Any]) -> str:
    """Generates a human-readable standardized descriptor string.

    Format: SUBCATEGORY | KEY_ATTR_1 | KEY_ATTR_2 | ...
    """
    parts = [subcategory]
    spec = default_registry.get_spec(subcategory)

    if spec:
        for attr_spec in spec.attributes:
            val = attributes.get(attr_spec.name)
            if val is not None and val != "":
                parts.append(str(val))
    else:
        for k, v in sorted(attributes.items()):
            if v is not None and v != "":
                parts.append(f"{k}:{v}")

    return " | ".join(parts)


def generate_canonical_text(descriptor: str) -> str:
    """Derives canonical normalized text from the descriptor."""
    return descriptor.replace(" | ", " ").strip().upper()


def generate_unique_mpng_code() -> str:
    """Generates an opaque 17-character Verhoeff-protected national code."""
    # 10-digit random integer
    seq = random.randint(100_000_000, 9_999_999_999)
    return make_code(seq)


async def create_golden_master(
    session: AsyncSession,
    subcategory: str,
    attributes: dict[str, Any],
    canonical_uom: str = "EA",
    status: str = "DRAFT",
    actor_id: UUID | None = None,
    is_proprietary: bool = False,
    oem_name: str | None = None,
    oem_part_number: str | None = None,
    unspsc_code: str | None = None,
    gem_category_id: str | None = None,
    rationale: str = "New master creation",
) -> GoldenMaster:
    """Creates a new Golden Master with transactional audit logging."""
    if status not in ("DRAFT", "ACTIVE", "DEPRECATED"):
        raise LifecycleError(f"Invalid initial master status: {status}")

    major = SUBCATEGORY_MAP.get(subcategory, subcategory.split(".")[0])
    spec = default_registry.get_spec(subcategory)
    identity_mode = spec.identity_mode.value if spec else "PARAMETRIC"
    segment = spec.segment if spec else ["COMMON"]

    block_key, _ = compute_block_key(subcategory, attributes)
    descriptor = generate_descriptor(subcategory, attributes)
    canonical_text = generate_canonical_text(descriptor)
    code = generate_unique_mpng_code()

    master = GoldenMaster(
        id=uuid4(),
        code=code,
        descriptor=descriptor,
        status=status,
        major_category=major,
        subcategory=subcategory,
        block_key=block_key,
        identity_mode=identity_mode,
        segment=segment,
        attributes=attributes,
        is_proprietary=is_proprietary,
        oem_name_norm=oem_name.strip().upper() if oem_name else None,
        oem_part_number_norm=oem_part_number.strip().upper() if oem_part_number else None,
        canonical_text=canonical_text,
        canonical_uom=canonical_uom,
        unspsc_code=unspsc_code,
        gem_category_id=gem_category_id,
    )

    session.add(master)
    await session.flush()

    # Write transactional audit log
    after_state = json.dumps(
        {
            "code": code,
            "descriptor": descriptor,
            "status": status,
            "subcategory": subcategory,
            "attributes": attributes,
        }
    )
    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'CREATE_MASTER', 'golden_masters', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": actor_id,
            "entity_id": str(master.id),
            "after": after_state,
            "rationale": rationale,
        },
    )

    return master


async def update_master_status(
    session: AsyncSession,
    master_id: UUID,
    new_status: str,
    actor_id: UUID | None = None,
    rationale: str = "",
) -> GoldenMaster:
    """Transitions a Golden Master lifecycle state with audit record."""
    stmt = select(GoldenMaster).where(GoldenMaster.id == master_id)
    res = await session.execute(stmt)
    master = res.scalar_one_or_none()
    if not master:
        raise LifecycleError(f"Golden Master {master_id} not found")

    old_status = master.status
    if old_status == new_status:
        return master

    valid_transitions = {
        "DRAFT": {"ACTIVE", "DEPRECATED"},
        "ACTIVE": {"DEPRECATED"},
        "DEPRECATED": set(),  # Terminal state
    }

    if new_status not in valid_transitions.get(old_status, set()):
        raise LifecycleError(f"Illegal status transition from {old_status} to {new_status}")

    master.status = new_status
    await session.flush()

    before_state = json.dumps({"status": old_status})
    after_state = json.dumps({"status": new_status})

    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'UPDATE_MASTER_STATUS', 'golden_masters', :entity_id, CAST(:before AS jsonb), CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": actor_id,
            "entity_id": str(master.id),
            "before": before_state,
            "after": after_state,
            "rationale": rationale or f"Status changed from {old_status} to {new_status}",
        },
    )

    return master


async def merge_golden_masters(
    session: AsyncSession,
    source_id: UUID,
    target_id: UUID,
    actor_id: UUID | None = None,
    rationale: str = "",
) -> tuple[GoldenMaster, GoldenMaster]:
    """Merges source master into target master.

    Sets source status to DEPRECATED with merged_into redirect pointer.
    Reassigns aliases and raw items from source to target.
    """
    if source_id == target_id:
        raise LifecycleError("Cannot merge a master into itself")

    s_res = await session.execute(select(GoldenMaster).where(GoldenMaster.id == source_id))
    source = s_res.scalar_one_or_none()
    t_res = await session.execute(select(GoldenMaster).where(GoldenMaster.id == target_id))
    target = t_res.scalar_one_or_none()

    if not source or not target:
        raise LifecycleError("Source or target master not found")

    if target.status == "DEPRECATED":
        raise LifecycleError("Cannot merge into a deprecated master")

    # Deprecate source and set redirect pointer
    source.status = "DEPRECATED"
    source.merged_into = target_id

    # Reassign golden aliases
    await session.execute(update(GoldenAlias).where(GoldenAlias.golden_id == source_id).values(golden_id=target_id))

    # Reassign raw items
    await session.execute(update(RawItem).where(RawItem.golden_id == source_id).values(golden_id=target_id))

    await session.flush()

    # Audit log
    before_state = json.dumps({"status": source.status, "merged_into": None})
    after_state = json.dumps(
        {
            "status": "DEPRECATED",
            "merged_into": str(target_id),
            "target_code": target.code,
        }
    )

    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'MERGE_MASTERS', 'golden_masters', :entity_id, CAST(:before AS jsonb), CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": actor_id,
            "entity_id": str(source.id),
            "before": before_state,
            "after": after_state,
            "rationale": rationale or f"Merged master {source.code} into {target.code}",
        },
    )

    return source, target


async def split_golden_master(
    session: AsyncSession,
    source_id: UUID,
    new_masters_data: list[dict[str, Any]],
    raw_item_reassignments: dict[UUID, int],  # raw_id -> index in new_masters_data
    actor_id: UUID | None = None,
    rationale: str = "",
) -> list[GoldenMaster]:
    """Splits an existing golden master into multiple new masters.

    The original master is marked DEPRECATED.
    Designated raw items are reassigned; unassigned items return to PENDING queue.
    """
    s_res = await session.execute(select(GoldenMaster).where(GoldenMaster.id == source_id))
    source = s_res.scalar_one_or_none()
    if not source:
        raise LifecycleError(f"Source master {source_id} not found")

    if not new_masters_data or len(new_masters_data) < 2:
        raise LifecycleError("Splitting requires at least 2 target master specifications")

    # Create new target masters
    created_targets: list[GoldenMaster] = []
    for m_data in new_masters_data:
        target = await create_golden_master(
            session=session,
            subcategory=m_data.get("subcategory", source.subcategory),
            attributes=m_data["attributes"],
            canonical_uom=m_data.get("canonical_uom", source.canonical_uom),
            status=m_data.get("status", "ACTIVE"),
            actor_id=actor_id,
            rationale=f"Result of splitting {source.code}",
        )
        created_targets.append(target)

    # Reassign raw items
    for raw_id, target_idx in raw_item_reassignments.items():
        if 0 <= target_idx < len(created_targets):
            new_target = created_targets[target_idx]
            await session.execute(update(RawItem).where(RawItem.id == raw_id).values(golden_id=new_target.id))

    # Any remaining raw items linked to source that were not reassigned return to queue
    reassigned_raw_ids = list(raw_item_reassignments.keys())
    if reassigned_raw_ids:
        await session.execute(
            update(RawItem)
            .where(RawItem.golden_id == source_id, RawItem.id.not_in(reassigned_raw_ids))
            .values(golden_id=None, status="PENDING")
        )
    else:
        await session.execute(
            update(RawItem).where(RawItem.golden_id == source_id).values(golden_id=None, status="PENDING")
        )

    # Mark source as DEPRECATED
    source.status = "DEPRECATED"
    await session.flush()

    # Log split in audit log
    after_state = json.dumps(
        {
            "status": "DEPRECATED",
            "split_into": [str(t.id) for t in created_targets],
            "target_codes": [t.code for t in created_targets],
        }
    )

    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'SPLIT_MASTER', 'golden_masters', :entity_id, NULL, CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": actor_id,
            "entity_id": str(source.id),
            "after": after_state,
            "rationale": rationale or f"Split master {source.code} into {len(created_targets)} masters",
        },
    )

    return created_targets


async def correct_master_attributes(
    session: AsyncSession,
    master_id: UUID,
    new_attributes: dict[str, Any],
    actor_id: UUID | None = None,
    rationale: str = "",
) -> GoldenMaster:
    """Corrects attributes of a golden master without modifying the permanent code."""
    res = await session.execute(select(GoldenMaster).where(GoldenMaster.id == master_id))
    master = res.scalar_one_or_none()
    if not master:
        raise LifecycleError(f"Golden Master {master_id} not found")

    before_attrs = dict(master.attributes or {})

    # Update attributes
    master.attributes = new_attributes
    master.block_key, _ = compute_block_key(master.subcategory, new_attributes)
    master.descriptor = generate_descriptor(master.subcategory, new_attributes)
    master.canonical_text = generate_canonical_text(master.descriptor)

    await session.flush()

    before_state = json.dumps({"attributes": before_attrs, "descriptor": master.descriptor})
    after_state = json.dumps({"attributes": new_attributes, "descriptor": master.descriptor})

    await session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash) "
            "VALUES (:actor, 'CORRECT_ATTRIBUTES', 'golden_masters', :entity_id, CAST(:before AS jsonb), CAST(:after AS jsonb), :rationale, '', '')"
        ),
        {
            "actor": actor_id,
            "entity_id": str(master.id),
            "before": before_state,
            "after": after_state,
            "rationale": rationale or "Attribute correction via steward review",
        },
    )

    return master
