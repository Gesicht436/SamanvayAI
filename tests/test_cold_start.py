"""Unit and integration tests for Cold-Start Deduplication Pipeline."""

import unittest

from api.services.cold_start import ColdStartEngine, RawItemRecord


class TestColdStartDeduplication(unittest.TestCase):
    def setUp(self):
        self.engine = ColdStartEngine(packs_dir="packs")

    def test_cluster_identical_signatures(self):
        """Identical HARD+REQUIRED attribute signatures collapse into one DRAFT master."""
        items = [
            RawItemRecord(
                item_code="ITEM-001",
                description="GATE VALVE 100 NB CL150 WCB FLANGED RF API600",
                qty=10.0,
                unit_price_inr=15000.0,
            ),
            RawItemRecord(
                item_code="ITEM-002",
                description="VLV GT 100NB 150# WCB FLG RF API 600",
                qty=5.0,
                unit_price_inr=15000.0,
            ),
            RawItemRecord(
                item_code="ITEM-003",
                description="100 NB CLASS 150 GATE VALVE WCB BODY FLANGED RF API 600",
                qty=2.0,
                unit_price_inr=15000.0,
            ),
            # Distinct item (different size 150 NB)
            RawItemRecord(
                item_code="ITEM-004",
                description="GATE VALVE 150 NB CL150 WCB FLANGED RF API600",
                qty=4.0,
                unit_price_inr=22000.0,
            ),
        ]

        clusters, report = self.engine.process_items(items)

        # 4 raw items should collapse into 2 distinct masters
        self.assertEqual(report.total_items, 4)
        self.assertEqual(report.total_masters, 2)
        self.assertEqual(report.dedup_percentage, 50.0)

        # Top cluster should contain the 3 identical 100NB valves
        top_clust = clusters[0]
        self.assertEqual(top_clust.member_count, 3)
        self.assertEqual(top_clust.total_qty, 17.0)
        self.assertEqual(top_clust.total_value_inr, 255000.0)
        self.assertTrue(top_clust.proposed_golden_code.startswith("MPNG-"))
        self.assertEqual(len(top_clust.proposed_golden_code), 17)

    def test_near_matches_subset_detection(self):
        """Near-signature differing only by missing attributes links as needs_review."""
        items = [
            # Full signature
            RawItemRecord(
                item_code="ITEM-FULL",
                description="GATE VALVE 100 NB CL150 WCB FLANGED RF API600",
            ),
            # Partial signature (missing pressure_class and standard, but shares size_nb and body)
            RawItemRecord(
                item_code="ITEM-PARTIAL",
                description="GATE VALVE 100 NB WCB",
            ),
        ]

        clusters, report = self.engine.process_items(items)
        self.assertEqual(report.total_masters, 2)

        # The partial cluster should link to the fuller cluster as near-match
        partial_clust = next(c for c in clusters if len(c.signature) < 4)
        full_clust = next(c for c in clusters if len(c.signature) >= 4)
        self.assertIn(full_clust.cluster_id, partial_clust.near_matches)

    def test_empty_items_handling(self):
        """Empty items list produces empty report without crashing."""
        clusters, report = self.engine.process_items([])
        self.assertEqual(clusters, [])
        self.assertEqual(report.total_items, 0)
        self.assertEqual(report.dedup_percentage, 0.0)


if __name__ == "__main__":
    unittest.main()
