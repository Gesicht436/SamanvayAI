"""Unit and integration tests for Stream B Forward Demand Pooling and Tender Packs (Section 8.1 & 13.0)."""

import unittest
import uuid
from datetime import date

from sqlalchemy import select

from api.database import SyncSessionLocal
from api.models.entities import AuditLog, GoldenMaster, SubcategorySpec, User
from api.services.pool import (
    calculate_pooling_discount,
    create_forward_indent,
    create_tender_pool,
    generate_tender_pack,
)


class TestDemandPoolingAndTenderPacks(unittest.TestCase):
    def test_discount_curve_thresholds(self):
        """Verify discount percentage curves across pooling classes per Section 19.1/19.2."""
        # BULK_MT: 5% at 50, 8% at 200, 12% at 500, 15% at 1000+
        self.assertEqual(calculate_pooling_discount("BULK_MT", 30.0), 0.02)
        self.assertEqual(calculate_pooling_discount("BULK_MT", 100.0), 0.05)
        self.assertEqual(calculate_pooling_discount("BULK_MT", 300.0), 0.08)
        self.assertEqual(calculate_pooling_discount("BULK_MT", 600.0), 0.12)
        self.assertEqual(calculate_pooling_discount("BULK_MT", 1200.0), 0.15)

        # BULK_M: 4% at 1000, 7% at 5000, 10% at 15000+
        self.assertEqual(calculate_pooling_discount("BULK_M", 500.0), 0.02)
        self.assertEqual(calculate_pooling_discount("BULK_M", 2000.0), 0.04)
        self.assertEqual(calculate_pooling_discount("BULK_M", 8000.0), 0.07)
        self.assertEqual(calculate_pooling_discount("BULK_M", 20000.0), 0.10)

        # ENGINEERED: 3% at 10, 6% at 50, 10% at 100+
        self.assertEqual(calculate_pooling_discount("ENGINEERED", 5.0), 0.01)
        self.assertEqual(calculate_pooling_discount("ENGINEERED", 20.0), 0.03)
        self.assertEqual(calculate_pooling_discount("ENGINEERED", 60.0), 0.06)
        self.assertEqual(calculate_pooling_discount("ENGINEERED", 150.0), 0.10)

    def test_forward_indent_creation_and_pooling(self):
        """Verify forward indent creation, multi-CPSE pooling, and transactional audit logging."""
        with SyncSessionLocal() as db:
            gm_id = uuid.uuid4()
            gm = GoldenMaster(
                id=gm_id,
                code=f"MPNG-POL-{str(gm_id)[:8]}",
                descriptor="SEAMLESS PIPE 200 NB SCH 40 ASTM A106 GR B",
                status="ACTIVE",
                major_category="PIPES",
                subcategory="PIPES.PIPE",
                block_key="PIP_SMLS_200_40",
                canonical_text="SEAMLESS PIPE 200 NB SCH 40 ASTM A106 GR B",
                canonical_uom="M",
                attributes={
                    "size_nb": 200,
                    "schedule": "SCH_40",
                    "material_grade": "A106_GR_B",
                    "manufacturing_method": "SEAMLESS",
                },
            )
            db.add(gm)

            # Ensure subcategory spec has pooling_class
            sub = db.execute(select(SubcategorySpec).where(SubcategorySpec.subcategory == "PIPES.PIPE")).scalar_one_or_none()
            if not sub:
                sub = SubcategorySpec(
                    subcategory="PIPES.PIPE",
                    segment=["COMMON"],
                    identity_mode="PARAMETRIC",
                    pooling_class="BULK_M",
                )
                db.add(sub)
            else:
                sub.pooling_class = "BULK_M"
            db.commit()

            user_oil = db.execute(select(User).where(User.subject == "usr-oil-maker-1")).scalar_one()
            user_power = db.execute(select(User).where(User.subject == "usr-power-maker-1")).scalar_one()

            # 1. Create indents from two different CPSEs
            ind_oil = create_forward_indent(
                db=db,
                org_id="OIL-1",
                user_id=user_oil.id,
                golden_id=gm.id,
                qty=3000.0,
                uom="M",
                need_by=date(2026, 12, 1),
                delivery_site="Mathura Refinery Store",
                plant="PLANT-MATHURA",
                budget_unit_cost=1800.0,
            )

            ind_power = create_forward_indent(
                db=db,
                org_id="POWER-1",
                user_id=user_power.id,
                golden_id=gm.id,
                qty=4000.0,
                uom="M",
                need_by=date(2027, 1, 15),
                delivery_site="Korba Thermal Power Station",
                plant="PLANT-KORBA",
                budget_unit_cost=1850.0,
            )

            self.assertEqual(ind_oil.status, "OPEN")
            self.assertEqual(ind_power.status, "OPEN")

            # 2. Pool indents into Joint Tender Pool (Lead: OIL-1)
            pool = create_tender_pool(
                db=db,
                lead_org_id="OIL-1",
                user_id=user_oil.id,
                indent_ids=[ind_oil.id, ind_power.id],
                mou_ref="MOU-OIL-POWER-PIPE-2026",
            )

            self.assertEqual(pool.lead_org, "OIL-1")
            self.assertEqual(float(pool.total_qty), 7000.0)
            self.assertEqual(pool.status, "POOLED")
            self.assertGreater(float(pool.estimated_savings), 0.0)

            # Verify indents status changed to POOLED
            db.refresh(ind_oil)
            db.refresh(ind_power)
            self.assertEqual(ind_oil.status, "POOLED")
            self.assertEqual(ind_power.status, "POOLED")

            # Verify transactional audit record
            audit = db.execute(
                select(AuditLog).where(
                    AuditLog.entity_id == str(pool.id),
                    AuditLog.action == "TENDER_POOL_CREATED",
                )
            ).scalar_one_or_none()
            self.assertIsNotNone(audit)
            self.assertEqual(audit.entity, "tender_pools")

            # 3. Generate structured Tender Pack
            pack_res = generate_tender_pack(db=db, pool_id=pool.id)
            self.assertEqual(pack_res["pool_id"], str(pool.id))

            pack = pack_res["tender_pack"]
            self.assertIn("Joint CPSE Supply Tender", pack["title"])
            self.assertEqual(pack["procurement_summary"]["total_pooled_qty"], 7000.0)
            self.assertEqual(len(pack["consignee_distribution"]), 2)
            self.assertTrue(any(c["org_id"] == "OIL-1" for c in pack["consignee_distribution"]))
            self.assertTrue(any(c["org_id"] == "POWER-1" for c in pack["consignee_distribution"]))

            # Verify CSV export
            csv_str = pack_res["csv_export"]
            self.assertIn("CONSIGNEE_ORG,PLANT,DELIVERY_SITE,ALLOCATED_QTY,UOM,NEED_BY", csv_str)
            self.assertIn("Mathura Refinery Store", csv_str)
            self.assertIn("Korba Thermal Power Station", csv_str)
