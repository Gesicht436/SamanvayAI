"""Unit tests for Candidate Retrieval and Scoring Engine."""

import unittest
from uuid import uuid4

from api.extractors.registry import IdentityMode, default_registry
from api.services.candidates import (
    RetrievedCandidate,
    compute_block_key,
    retrieve_candidates_in_memory,
)
from api.services.comparator import compare_items
from api.services.tiering import assign_tier


class TestCandidatesAndScoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        default_registry.load_packs("packs")

    def test_compute_block_key(self):
        """Block key uses primary dimension; missing primary dim flags PARTIAL_BLOCK."""
        # Valve: primary_dimension is size_nb (NB_MM)
        key, is_partial = compute_block_key("VALVES.GATE", {"size_nb": 100})
        self.assertFalse(is_partial)
        self.assertIn("100_NB_MM", key)

        # Missing size_nb -> PARTIAL_BLOCK
        key_missing, is_partial_missing = compute_block_key("VALVES.GATE", {"pressure_class": "ASME_150"})
        self.assertTrue(is_partial_missing)
        self.assertIn("NULL", key_missing)

    def test_in_memory_candidate_retrieval_priorities(self):
        """Verify 4-stage retrieval priority: Alias -> MPN -> Block -> Fuzzy."""
        c1 = RetrievedCandidate(
            golden_master_id=uuid4(),
            golden_code="MPNG-0000000001-9",
            descriptor="VALVES.GATE | 100 | ASME_150 | A216_WCB",
            subcategory="VALVES.GATE",
            canonical_text="VALVE GATE 100 NB CL150 WCB FLANGED RF",
            attributes={"size_nb": 100, "pressure_class": "ASME_150", "body_material": "A216_WCB"},
            block_key="VALVES:VALVES.GATE:size_nb=100_NB_MM",
        )
        c2 = RetrievedCandidate(
            golden_master_id=uuid4(),
            golden_code="MPNG-0000000002-7",
            descriptor="VALVES.GATE | 150 | ASME_300 | A216_WCB",
            subcategory="VALVES.GATE",
            canonical_text="VALVE GATE 150 NB CL300 WCB FLANGED RF",
            attributes={"size_nb": 150, "pressure_class": "ASME_300", "body_material": "A216_WCB"},
            block_key="VALVES:VALVES.GATE:size_nb=150_NB_MM",
            oem_part_number_norm="VLV-150-CL300",
        )
        pool = [c1, c2]

        # Stage 1: Exact alias match
        aliases_map = {str(c1.golden_master_id): ["LEGACY GATE VALVE 4 INCH"]}
        res_alias = retrieve_candidates_in_memory(
            candidate_pool=pool,
            clean_text="LEGACY GATE VALVE 4 INCH",
            subcategory="VALVES.GATE",
            extracted_attrs={"size_nb": 100},
            aliases_map=aliases_map,
        )
        self.assertGreaterEqual(len(res_alias), 1)
        self.assertTrue(res_alias[0].alias_exact)
        self.assertEqual(res_alias[0].golden_code, c1.golden_code)

        # Stage 2: OEM part number match
        res_mpn = retrieve_candidates_in_memory(
            candidate_pool=pool,
            clean_text="GATE VALVE VLV-150-CL300",
            subcategory="VALVES.GATE",
            extracted_attrs={"part_number": "VLV-150-CL300", "size_nb": 150},
        )
        self.assertEqual(res_mpn[0].golden_code, c2.golden_code)
        self.assertTrue(res_mpn[0].mpn_exact)

        # Stage 3: Block match
        res_block = retrieve_candidates_in_memory(
            candidate_pool=pool,
            clean_text="GATE VALVE 100 NB",
            subcategory="VALVES.GATE",
            extracted_attrs={"size_nb": 100},
        )
        self.assertEqual(res_block[0].golden_code, c1.golden_code)
        self.assertFalse(res_block[0].is_partial_block)

        # Stage 4: Missing primary dim -> Fallback marked PARTIAL_BLOCK
        res_fallback = retrieve_candidates_in_memory(
            candidate_pool=pool,
            clean_text="GATE VALVE WCB",
            subcategory="VALVES.GATE",
            extracted_attrs={"body_material": "A216_WCB"},  # size_nb missing
        )
        self.assertTrue(res_fallback[0].is_partial_block)

    def test_invariant_s9_scoring_never_raises_tier1(self):
        """Invariant S9: Scoring probability may lower a tier, never raise a gated item to Tier 1."""
        req_attrs = {
            "size_nb": 100,
            "pressure_class": "ASME_150",
            "body_material": "A216_WCB",
            "end_connection": "FLANGED",
            "facing": "RF",
            "design_standard": "API_600",
            # REQUIRED trim_code missing!
        }
        cand_attrs = {
            "size_nb": 100,
            "pressure_class": "ASME_150",
            "body_material": "A216_WCB",
            "end_connection": "FLANGED",
            "facing": "RF",
            "design_standard": "API_600",
            "trim_code": "API_TRIM_8",
            "bonnet_type": "BOLTED",
            "operator": "HANDWHEEL",
            "fire_safe": "API_607",
            "sour_service": "NO",
        }
        comp = compare_items(req_attrs, cand_attrs, "VALVES.GATE")
        self.assertTrue(comp.has_missing_required)

        # Even with artificial 1.0 probability, tier must remain Tier 2 (Review)
        tier_res = assign_tier(
            comparison=comp,
            identity_mode=IdentityMode.PARAMETRIC,
            probability=1.0,
            tau_auto=0.95,
        )
        self.assertEqual(tier_res.tier, 2)
        self.assertIn("MISSING_REQUIRED_ATTRIBUTE", tier_res.reason_codes)

        # Conversely, if prob < tau_auto on a perfect comparison, prob LOWERS tier to Tier 2
        perfect_comp = compare_items(cand_attrs, cand_attrs, "VALVES.GATE")
        self.assertFalse(perfect_comp.has_hard_mismatch)
        self.assertFalse(perfect_comp.has_missing_required)

        tier_lowered = assign_tier(
            comparison=perfect_comp,
            identity_mode=IdentityMode.PARAMETRIC,
            probability=0.80,  # Below tau_auto 0.95
            tau_auto=0.95,
        )
        self.assertEqual(tier_lowered.tier, 2)
        self.assertIn("PROBABILITY_REVIEW_RANGE", tier_lowered.reason_codes)


if __name__ == "__main__":
    unittest.main()
