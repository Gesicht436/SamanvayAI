"""Unit and integration tests for Stream A Surplus Stock Transfers (Section 8.1 & 13.0)."""

import unittest
import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select

from api.database import SyncSessionLocal
from api.models.entities import AuditLog, GoldenMaster, StockLot, User
from api.services.transfer import (
    request_transfer,
    review_transfer_gate,
)


class TestStreamATransfers(unittest.TestCase):
    def test_request_transfer_success_and_value_model(self):
        """Verify successful creation of transfer requisition and value calculation."""
        with SyncSessionLocal() as db:
            gm_id = uuid.uuid4()
            gm = GoldenMaster(
                id=gm_id,
                code=f"MPNG-TRF-{str(gm_id)[:8]}",
                descriptor="FLANGE WNRF 100 NB CL300 A105",
                status="ACTIVE",
                major_category="FLANGES",
                subcategory="FLANGES.FLANGE",
                block_key="FLG_WN_100_300",
                canonical_text="FLANGE WNRF 100 NB CL300 A105",
                canonical_uom="EA",
            )
            db.add(gm)

            lot_id = uuid.uuid4()
            lot = StockLot(
                id=lot_id,
                org_id="OIL-1",
                golden_id=gm.id,
                plant="PLANT-MATHURA",
                qty_remaining=50.0,
                mfg_date=date(2025, 1, 1),
                expiry_date=date(2028, 1, 1),
            )
            db.add(lot)
            db.commit()

            # Fetch seeded user
            maker_user = db.execute(select(User).where(User.subject == "usr-power-maker-1")).scalar_one_or_none()
            if not maker_user:
                maker_user = User(id=uuid.uuid4(), org_id="POWER-1", subject="test-power-maker", role="MAKER")
                db.add(maker_user)
                db.commit()

            order = request_transfer(
                db=db,
                to_org_id="POWER-1",
                user_id=maker_user.id,
                lot_id=lot.id,
                requested_qty=20.0,
                to_plant="PLANT-KORBA",
                basis="BOOK_VALUE",
                agreed_price=1000.0,
            )

            self.assertEqual(order.from_org, "OIL-1")
            self.assertEqual(order.to_org, "POWER-1")
            self.assertEqual(float(order.qty), 20.0)
            self.assertEqual(order.state, "REQUESTED")
            self.assertGreater(float(order.avoided_purchase_cost), float(order.transfer_cost))
            self.assertGreater(float(order.net_benefit), 0.0)


            # Verify audit entry was written in the same transaction
            audit = db.execute(
                select(AuditLog).where(
                    AuditLog.entity_id == str(order.id),
                    AuditLog.action == "TRANSFER_REQUESTED",
                )
            ).scalar_one_or_none()
            self.assertIsNotNone(audit)
            self.assertEqual(audit.entity, "transfer_orders")

    def test_invariant_s6_blocks_expired_lot_transfer(self):
        """Verify Invariant S6: Expired lot cannot be transferred under Stream A."""
        with SyncSessionLocal() as db:
            gm_id = uuid.uuid4()
            gm = GoldenMaster(
                id=gm_id,
                code=f"MPNG-S6-{str(gm_id)[:8]}",
                descriptor="REFRACTORY MORTAR FIRECLAY 50 KG",
                status="ACTIVE",
                major_category="REFRACTORY",
                subcategory="STEEL.REFRACTORY",
                block_key="REF_MORTAR_50",
                canonical_text="REFRACTORY MORTAR FIRECLAY 50 KG",
                canonical_uom="BAG",
            )
            db.add(gm)

            # Expired lot in 2024
            lot_expired = StockLot(
                id=uuid.uuid4(),
                org_id="STEEL-1",
                golden_id=gm.id,
                plant="PLANT-BHILAI",
                qty_remaining=100.0,
                mfg_date=date(2023, 1, 1),
                expiry_date=date(2024, 1, 1),  # Expired
            )
            db.add(lot_expired)
            db.commit()

            with self.assertRaises(HTTPException) as ctx:
                request_transfer(
                    db=db,
                    to_org_id="POWER-1",
                    user_id=uuid.uuid4(),
                    lot_id=lot_expired.id,
                    requested_qty=10.0,
                )
            self.assertEqual(ctx.exception.status_code, 422)
            self.assertIn("Invariant S6 Violation", ctx.exception.detail)

    def test_maker_checker_invariant_blocks_self_approval(self):
        """Verify Maker != Checker invariant: Proposer cannot approve their own transfer order."""
        with SyncSessionLocal() as db:
            gm_id = uuid.uuid4()
            gm = GoldenMaster(
                id=gm_id,
                code=f"MPNG-MC-{str(gm_id)[:8]}",
                descriptor="BALL BEARING 6312 2RS C3",
                status="ACTIVE",
                major_category="BEARINGS",
                subcategory="BEARINGS.BEARING",
                block_key="BRG_6312",
                canonical_text="BALL BEARING 6312 2RS C3",
                canonical_uom="EA",
            )
            db.add(gm)

            lot = StockLot(
                id=uuid.uuid4(),
                org_id="MINE-1",
                golden_id=gm.id,
                plant="PLANT-DHANBAD",
                qty_remaining=30.0,
                mfg_date=date(2025, 1, 1),
                expiry_date=date(2029, 1, 1),
            )
            db.add(lot)
            db.commit()

            maker = db.execute(select(User).where(User.subject == "usr-steel-maker-1")).scalar_one_or_none()
            if not maker:
                maker = User(id=uuid.uuid4(), org_id="STEEL-1", subject="test-steel-maker", role="MAKER")
                db.add(maker)
                db.commit()

            checker = db.execute(select(User).where(User.subject == "usr-steel-checker-1")).scalar_one_or_none()
            if not checker:
                checker = User(id=uuid.uuid4(), org_id="STEEL-1", subject="test-steel-checker", role="CHECKER")
                db.add(checker)
                db.commit()

            order = request_transfer(
                db=db,
                to_org_id="STEEL-1",
                user_id=maker.id,
                lot_id=lot.id,
                requested_qty=5.0,
            )

            # Maker attempts to approve their own transfer order
            with self.assertRaises(HTTPException) as ctx:
                review_transfer_gate(
                    db=db,
                    transfer_id=order.id,
                    user_id=maker.id,
                    action="APPROVED",
                    rationale="Self approval attempt",
                )
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertIn("MAKER_CHECKER_VIOLATION", ctx.exception.detail)

            # Different checker approves successfully and stock is deducted
            approved_order = review_transfer_gate(
                db=db,
                transfer_id=order.id,
                user_id=checker.id,
                action="APPROVED",
                rationale="Approved by domain steward after MTC verification",
                mtc_uploaded=True,
            )

            self.assertEqual(approved_order.state, "APPROVED")
            self.assertTrue(approved_order.mtc_uploaded)

            # Verify stock deduction
            db.refresh(lot)
            self.assertEqual(float(lot.qty_remaining), 25.0)
