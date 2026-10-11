"""Unit tests for api.core utilities: Verhoeff, HashChain, Trigram, and Jaro-Winkler.
Standard library unittest, runnable via `uv run pytest tests/test_core_utils.py`.
"""

import unittest

from api.core.hashchain import GENESIS, build_chain, canonical, entry_hash, verify_chain
from api.core.jaro_winkler import jaro, jaro_winkler
from api.core.trigram import similarity, top_k, trigrams
from api.core.verhoeff import check_digit, is_valid, make_code, validate_code


class TestVerhoeff(unittest.TestCase):
    def test_known_vectors(self):
        self.assertEqual(check_digit("236"), "3")
        self.assertEqual(check_digit("12345"), "1")
        self.assertEqual(check_digit("0004821937"), "3")
        self.assertTrue(is_valid("2363"))
        self.assertTrue(is_valid("123451"))
        self.assertTrue(is_valid("00048219373"))

    def test_all_single_digit_errors_detected(self):
        sample = "00048219373"
        for i, original in enumerate(sample):
            for replacement in "0123456789":
                if replacement == original:
                    continue
                mutated = sample[:i] + replacement + sample[i + 1 :]
                self.assertFalse(is_valid(mutated), f"Failed to detect single digit error at {i}: {mutated}")

    def test_all_adjacent_transpositions_detected(self):
        sample = "00048219373"
        for i in range(len(sample) - 1):
            if sample[i] == sample[i + 1]:
                continue
            chars = list(sample)
            chars[i], chars[i + 1] = chars[i + 1], chars[i]
            mutated = "".join(chars)
            self.assertFalse(is_valid(mutated), f"Failed to detect adjacent transposition at {i}: {mutated}")

    def test_code_format(self):
        code = make_code(4821937)
        self.assertEqual(code, "MPNG-0004821937-3")
        self.assertEqual(len(code), 17)
        self.assertTrue(validate_code(code))
        self.assertFalse(validate_code("MPNG-0004821937-4"))
        self.assertFalse(validate_code("MPNG-0004821973-3"))
        self.assertFalse(validate_code("XYZ-0004821937-3"))
        self.assertFalse(validate_code("short"))

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            check_digit("12a4")
        with self.assertRaises(ValueError):
            check_digit("")
        with self.assertRaises(ValueError):
            make_code(0)
        with self.assertRaises(ValueError):
            make_code(10**10)


class TestTrigram(unittest.TestCase):
    def test_known_trigrams(self):
        grams = trigrams("valve")
        self.assertIn("  v", grams)
        self.assertIn(" va", grams)
        self.assertIn("val", grams)
        self.assertIn("alv", grams)
        self.assertIn("lve", grams)
        self.assertIn("ve ", grams)
        self.assertEqual(len(grams), 6)

    def test_similarity_properties(self):
        self.assertEqual(similarity("pipe", "pipe"), 1.0)
        self.assertEqual(similarity("pipe", "valve"), 0.0)
        self.assertAlmostEqual(similarity("flange", "gasket"), similarity("gasket", "flange"))
        self.assertEqual(similarity("", ""), 0.0)
        self.assertEqual(similarity("test", ""), 0.0)

    def test_unicode_and_punctuation(self):
        sim = similarity("100 NB Class-150", "100NB CLASS 150")
        self.assertGreater(sim, 0.70)

    def test_noise_ranks_below_match(self):
        candidates = [(1, "GATE VALVE 150#"), (2, "GLOBE VALVE 150#"), (3, "BALL VALVE 150#"), (4, "CENTRIFUGAL PUMP")]
        ranked = top_k("GATE VALVE 150#", candidates, k=2)
        self.assertEqual(ranked[0][1], 1)
        self.assertEqual(ranked[0][0], 1.0)


class TestJaroWinkler(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(jaro("MARTHA", "MARHTA"), jaro("MARHTA", "MARTHA"))
        self.assertAlmostEqual(jaro("MARTHA", "MARHTA"), 0.944, places=2)
        self.assertGreater(jaro_winkler("MARTHA", "MARHTA"), jaro("MARTHA", "MARHTA"))

    def test_symmetry(self):
        self.assertAlmostEqual(jaro_winkler("CRANE", "CROWN"), jaro_winkler("CROWN", "CRANE"))

    def test_edges(self):
        self.assertEqual(jaro("", ""), 0.0)
        self.assertEqual(jaro_winkler("", "test"), 0.0)
        self.assertEqual(jaro_winkler("test", "test"), 1.0)


class TestHashChain(unittest.TestCase):
    def test_valid_chain(self):
        records = [
            {"action": "CREATE", "entity": "master", "id": 1},
            {"action": "UPDATE", "entity": "master", "id": 1, "status": "ACTIVE"},
        ]
        chain = build_chain(records)
        ok, broken_seq = verify_chain(chain)
        self.assertTrue(ok)
        self.assertIsNone(broken_seq)

    def test_edit_detected(self):
        records = [{"action": "CREATE", "id": 1}, {"action": "UPDATE", "id": 2}]
        chain = build_chain(records)
        chain[0]["record"]["action"] = "TAMPERED"
        ok, broken = verify_chain(chain)
        self.assertFalse(ok)
        self.assertEqual(broken, 1)

    def test_delete_and_reorder_detected(self):
        records = [{"id": 1}, {"id": 2}, {"id": 3}]
        chain = build_chain(records)
        chain_reordered = [chain[0], chain[2], chain[1]]
        ok, _broken = verify_chain(chain_reordered)
        self.assertFalse(ok)

    def test_key_order_does_not_matter(self):
        rec_a = {"z": 1, "a": 2}
        rec_b = {"a": 2, "z": 1}
        self.assertEqual(canonical(rec_a), canonical(rec_b))
        self.assertEqual(entry_hash(GENESIS, rec_a), entry_hash(GENESIS, rec_b))

    def test_unicode_record(self):
        rec = {"description": "वाल्व गेट 100 एनबी"}
        h = entry_hash(GENESIS, rec)
        self.assertEqual(len(h), 64)


if __name__ == "__main__":
    unittest.main()
