"""Unit and integration tests for Inter-CPSE Spare Locator (Section 12.0 & 13.2)."""

import unittest
import uuid
from datetime import date

from api.database import SyncSessionLocal
from api.models.entities import GoldenMaster, StockLot
from api.services.locator import (
    haversine_distance_km,
    quantity_bucket,
    search_spare_locator,
)


class TestSpareLocator(unittest.TestCase):
    def test_haversine_distance_math(self):
        """Verify Haversine spherical distance calculations."""
        # Mathura (27.4924, 77.6737) to New Delhi (28.6139, 77.2090) ~ 132 km
        dist = haversine_distance_km(27.4924, 77.6737, 28.6139, 77.2090)
        self.assertGreater(dist, 120.0)
        self.assertLess(dist, 145.0)

        # Distance to self is 0.0
        self.assertEqual(haversine_distance_km(22.3595, 82.7501, 22.3595, 82.7501), 0.0)

    def test_quantity_bucket_thresholds(self):
        """Verify privacy disclosure quantity buckets per Section 9.3."""
        self.assertEqual(quantity_bucket(5.0), "LOW (<10)")
        self.assertEqual(quantity_bucket(9.99), "LOW (<10)")
        self.assertEqual(quantity_bucket(10.0), "MEDIUM (10-50)")
        self.assertEqual(quantity_bucket(50.0), "MEDIUM (10-50)")
        self.assertEqual(quantity_bucket(50.1), "HIGH (>50)")
        self.assertEqual(quantity_bucket(1000.0), "HIGH (>50)")

    def test_search_spare_locator_with_privacy_masking(self):
        """Verify search results mask external CPSE details while revealing own inventory."""
        with SyncSessionLocal() as db:
            # 1. Setup Golden Master
            gm_id = uuid.uuid4()
            gm = GoldenMaster(
                id=gm_id,
                code=f"MPNG-LOC-{str(gm_id)[:8]}",
                descriptor="GATE VALVE 150 NB CL150 WCB RF",
                status="ACTIVE",
                major_category="VALVES",
                subcategory="VALVES.GATE",
                block_key="VLV_GT_150_150",
                canonical_text="GATE VALVE 150 NB CL150 WCB RF",
                canonical_uom="EA",
            )
            db.add(gm)

            # 2. Add StockLot for OIL-1 (Mathura)
            lot_oil = StockLot(
                id=uuid.uuid4(),
                org_id="OIL-1",
                golden_id=gm.id,
                plant="PLANT-MATHURA",
                qty_remaining=45.0,
                mfg_date=date(2025, 1, 1),
                expiry_date=date(2028, 1, 1),
            )
            db.add(lot_oil)

            # 3. Add StockLot for POWER-1 (Korba)
            lot_power = StockLot(
                id=uuid.uuid4(),
                org_id="POWER-1",
                golden_id=gm.id,
                plant="PLANT-KORBA",
                qty_remaining=120.0,
                mfg_date=date(2025, 2, 1),
                expiry_date=date(2028, 2, 1),
            )
            db.add(lot_power)
            db.commit()

            # Search from OIL-1 perspective
            res = search_spare_locator(
                db=db,
                current_org_id="OIL-1",
                golden_id=str(gm.id),
                requester_plant_code="PLANT-MATHURA",
            )

            self.assertGreaterEqual(res["total_results"], 2)
            results = res["results"]

            # Own lot (OIL-1) must be unmasked
            own_item = next(item for item in results if item["lot_id"] == str(lot_oil.id))
            self.assertTrue(own_item["is_own_inventory"])
            self.assertEqual(own_item["owner_org_id"], "OIL-1")
            self.assertEqual(own_item["exact_qty"], 45.0)
            self.assertEqual(own_item["plant_code"], "PLANT-MATHURA")
            self.assertFalse(own_item["can_request_transfer"])

            # Partner lot (POWER-1) must be masked per Section 9.3 & 13.2
            partner_item = next(item for item in results if item["lot_id"] == str(lot_power.id))
            self.assertFalse(partner_item["is_own_inventory"])
            self.assertEqual(partner_item["owner_org_id"], "PARTNER_CPSE")
            self.assertIsNone(partner_item["exact_qty"])
            self.assertEqual(partner_item["quantity_bucket"], "HIGH (>50)")
            self.assertEqual(partner_item["city"], "Korba")
            self.assertGreater(partner_item["air_distance_km"], 0.0)
            self.assertTrue(partner_item["can_request_transfer"])
