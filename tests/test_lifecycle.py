"""Integration tests for Golden Master Lifecycle service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from api.core.verhoeff import validate_code
from api.database import get_async_engine
from api.extractors.registry import default_registry
from api.models.entities import Organization, RawItem
from api.services.lifecycle import (
    LifecycleError,
    correct_master_attributes,
    create_golden_master,
    generate_canonical_text,
    generate_descriptor,
    merge_golden_masters,
    update_master_status,
)


@pytest.fixture(autouse=True)
def setup_packs():
    default_registry.load_packs("packs")


def test_descriptor_and_canonical_text():
    """Verify descriptor formatting and canonical text generation."""
    attrs = {
        "size_nb": 100,
        "pressure_class": "ASME_150",
        "body_material": "A216_WCB",
        "end_connection": "FLANGED",
        "facing": "RF",
        "design_standard": "API_600",
    }
    desc = generate_descriptor("VALVES.GATE", attrs)
    self_canonical = generate_canonical_text(desc)

    assert "VALVES.GATE" in desc
    assert "100" in desc
    assert "ASME_150" in desc
    assert "VALVES.GATE" in self_canonical
    assert "100" in self_canonical


@pytest.mark.asyncio
async def test_create_golden_master_and_audit():
    """Creating a golden master writes master and audit log in same transaction."""
    engine = get_async_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        attrs = {
            "size_nb": 150,
            "pressure_class": "ASME_300",
            "body_material": "A216_WCB",
            "end_connection": "FLANGED",
            "facing": "RF",
            "design_standard": "API_600",
        }
        master = await create_golden_master(
            session=session,
            subcategory="VALVES.GATE",
            attributes=attrs,
            canonical_uom="EA",
            status="DRAFT",
            rationale="Initial catalog bootstrap",
        )
        await session.commit()

        assert master.id is not None
        assert master.code.startswith("MPNG-")
        assert len(master.code) == 17
        assert validate_code(master.code) is True
        assert master.status == "DRAFT"

        # Verify audit log entry was written
        audit_res = await session.execute(
            text("SELECT action, entity, entity_id FROM audit_log WHERE entity_id = :eid"),
            {"eid": str(master.id)},
        )
        audit_row = audit_res.mappings().first()
        assert audit_row is not None
        assert audit_row["action"] == "CREATE_MASTER"
        assert audit_row["entity"] == "golden_masters"


@pytest.mark.asyncio
async def test_update_master_status_transitions():
    """Verify legal vs illegal status transitions."""
    engine = get_async_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        attrs = {"nominal_diameter_mm": 25, "strength_grade": "FE_500D"}
        master = await create_golden_master(
            session=session,
            subcategory="STEEL.REBAR",
            attributes=attrs,
            status="DRAFT",
        )
        await session.commit()

        # DRAFT -> ACTIVE (legal)
        active_master = await update_master_status(
            session=session,
            master_id=master.id,
            new_status="ACTIVE",
            rationale="Steward approved",
        )
        await session.commit()
        assert active_master.status == "ACTIVE"

        # ACTIVE -> DEPRECATED (legal)
        dep_master = await update_master_status(
            session=session,
            master_id=master.id,
            new_status="DEPRECATED",
            rationale="Item discontinued",
        )
        await session.commit()
        assert dep_master.status == "DEPRECATED"

        # DEPRECATED -> ACTIVE (illegal: terminal state)
        with pytest.raises(LifecycleError, match="Illegal status transition"):
            await update_master_status(
                session=session,
                master_id=master.id,
                new_status="ACTIVE",
            )


@pytest.mark.asyncio
async def test_merge_masters():
    """Merging source into target updates status, sets redirect, and reassigns raw items."""
    engine = get_async_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        # Ensure OIL-1 organization exists
        org_res = await session.execute(text("SELECT id FROM organizations WHERE id = 'OIL-1'"))
        if not org_res.first():
            session.add(Organization(id="OIL-1", name="Oil Corp", segment=["OIL"]))
            await session.flush()

        source = await create_golden_master(
            session=session,
            subcategory="PIPES.PIPE",
            attributes={"size_nb": 100, "schedule": "SCH_40", "material_spec": "A106_GR_B"},
            status="ACTIVE",
        )
        target = await create_golden_master(
            session=session,
            subcategory="PIPES.PIPE",
            attributes={"size_nb": 100, "schedule": "SCH_40", "material_spec": "A106_GR_B"},
            status="ACTIVE",
        )

        # Create raw item linked to source
        raw = RawItem(
            org_id="OIL-1",
            raw_description="PIPE 100 NB SCH 40 A106 B",
            raw_payload={},
            golden_id=source.id,
        )
        session.add(raw)
        await session.flush()

        # Execute merge
        merged_source, _merged_target = await merge_golden_masters(
            session=session,
            source_id=source.id,
            target_id=target.id,
            rationale="Duplicate catalog entry consolidation",
        )
        await session.commit()

        assert merged_source.status == "DEPRECATED"
        assert merged_source.merged_into == target.id

        # Raw item should now point to target
        await session.refresh(raw)
        assert raw.golden_id == target.id


@pytest.mark.asyncio
async def test_correct_attributes_code_immutability():
    """Attribute correction updates descriptor and attributes while keeping code immutable."""
    engine = get_async_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        initial_attrs = {"thread_size": "M24", "length_mm": 150, "bolt_grade": "A193_B7"}
        master = await create_golden_master(
            session=session,
            subcategory="FASTENERS.STUD_BOLT",
            attributes=initial_attrs,
            status="ACTIVE",
        )
        await session.commit()

        original_code = master.code
        updated_attrs = {"thread_size": "M24", "length_mm": 160, "bolt_grade": "A193_B7"}

        corrected = await correct_master_attributes(
            session=session,
            master_id=master.id,
            new_attributes=updated_attrs,
            rationale="Steward corrected fastener length",
        )
        await session.commit()

        # Code MUST never change
        assert corrected.code == original_code
        assert corrected.attributes["length_mm"] == 160
        assert "160" in corrected.descriptor
