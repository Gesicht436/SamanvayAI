import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import verhoeff, trigram, jaro_winkler, hashchain  # noqa: E402


class TestVerhoeff(unittest.TestCase):
    def test_known_vectors(self):
        for num, chk in [("236", "3"), ("12345", "1"), ("0004821937", "3"),
                         ("0000000001", "4"), ("0000172846", "4"), ("0000255118", "9")]:
            self.assertEqual(verhoeff.check_digit(num), chk)
            self.assertTrue(verhoeff.is_valid(num + chk))

    def test_all_single_digit_errors_detected(self):
        full = "00048219373"
        for i in range(len(full)):
            for k in range(1, 10):
                bad = full[:i] + str((int(full[i]) + k) % 10) + full[i + 1:]
                self.assertFalse(verhoeff.is_valid(bad), bad)

    def test_all_adjacent_transpositions_detected(self):
        full = "00048219373"
        for i in range(len(full) - 1):
            if full[i] != full[i + 1]:
                bad = full[:i] + full[i + 1] + full[i] + full[i + 2:]
                self.assertFalse(verhoeff.is_valid(bad), bad)

    def test_code_format(self):
        self.assertEqual(verhoeff.make_code(4821937), "MPNG-0004821937-3")
        self.assertEqual(len(verhoeff.make_code(1)), 17)
        self.assertTrue(verhoeff.validate_code("MPNG-0004821937-3"))
        for bad in ["MPNG-0004821937-4", "MPNG-000482193-3", "XPNG-0004821937-3",
                    "MPNG-0004821937_3", "", None, "MPNG-000482193७-3"]:
            self.assertFalse(verhoeff.validate_code(bad), bad)

    def test_rejects_bad_input(self):
        for bad in ["", "12a", "١٢٣"]:
            with self.assertRaises(ValueError):
                verhoeff.check_digit(bad)
        with self.assertRaises(ValueError):
            verhoeff.make_code(0)


class TestTrigram(unittest.TestCase):
    def test_known_trigrams(self):
        self.assertEqual(trigram.trigrams("cat"), {"  c", " ca", "cat", "at "})

    def test_similarity_properties(self):
        pairs = [("gate valve 100 nb", "valve gate 100nb"), ("ball valve", "gate valve"), ("", ""), ("a", "")]
        for a, b in pairs:
            self.assertAlmostEqual(trigram.similarity(a, b), trigram.similarity(b, a))
            self.assertTrue(0.0 <= trigram.similarity(a, b) <= 1.0)
        self.assertEqual(trigram.similarity("abc", "abc"), 1.0)
        self.assertEqual(trigram.similarity("", ""), 0.0)

    def test_noise_ranks_below_match(self):
        cands = [(1, "GATE VALVE 100 NB CLASS 150 WCB"), (2, "BALL VALVE 25 NB CLASS 300 SS316"), (3, "CABLE 4C X 16 SQMM")]
        best = trigram.top_k("gate valve 100nb cl150 wcb", cands, k=3)
        self.assertEqual(best[0][1], 1)

    def test_unicode_and_punctuation(self):
        self.assertTrue(trigram.similarity("वाल्व गेट", "वाल्व गेट") >= 0.0)
        self.assertEqual(trigram.similarity("A-B/C", "a b c"), 1.0)


class TestJaroWinkler(unittest.TestCase):
    def test_known_values(self):
        self.assertAlmostEqual(jaro_winkler.jaro("MARTHA", "MARHTA"), 0.9444, places=3)
        self.assertAlmostEqual(jaro_winkler.jaro_winkler("MARTHA", "MARHTA"), 0.9611, places=3)
        self.assertAlmostEqual(jaro_winkler.jaro_winkler("DIXON", "DICKSONX"), 0.8133, places=3)

    def test_edges(self):
        self.assertEqual(jaro_winkler.jaro_winkler("", ""), 0.0)
        self.assertEqual(jaro_winkler.jaro_winkler("a", ""), 0.0)
        self.assertEqual(jaro_winkler.jaro_winkler("ABC", "ABC"), 1.0)
        self.assertEqual(jaro_winkler.jaro_winkler("ABC", "XYZ"), 0.0)

    def test_symmetry(self):
        for a, b in [("SIEMENS", "SIMENS"), ("KSB", "KBS"), ("6205-2RS", "6205 2RS")]:
            self.assertAlmostEqual(jaro_winkler.jaro(a, b), jaro_winkler.jaro(b, a))


class TestHashChain(unittest.TestCase):
    def setUp(self):
        self.rows = hashchain.build_chain([
            {"actor": "u1", "action": "PROPOSE", "target": "G-1"},
            {"actor": "u2", "action": "APPROVE", "target": "G-1"},
            {"actor": "u2", "action": "MERGE", "target": "G-2"}])

    def test_valid_chain(self):
        self.assertEqual(hashchain.verify_chain(self.rows), (True, None))

    def test_key_order_does_not_matter(self):
        a = hashchain.entry_hash(hashchain.GENESIS, {"a": 1, "b": 2})
        b = hashchain.entry_hash(hashchain.GENESIS, {"b": 2, "a": 1})
        self.assertEqual(a, b)

    def test_edit_detected(self):
        rows = copy.deepcopy(self.rows)
        rows[1]["record"]["action"] = "REJECT"
        self.assertEqual(hashchain.verify_chain(rows), (False, 2))

    def test_delete_and_reorder_detected(self):
        self.assertFalse(hashchain.verify_chain([self.rows[0], self.rows[2]])[0])
        self.assertFalse(hashchain.verify_chain([self.rows[1], self.rows[0], self.rows[2]])[0])

    def test_unicode_record(self):
        rows = hashchain.build_chain([{"note": "वाल्व 100 NB"}])
        self.assertTrue(hashchain.verify_chain(rows)[0])


if __name__ == "__main__":
    unittest.main()
