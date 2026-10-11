import json, os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(__file__))
from clopper_pearson import clopper_pearson, upper_bound_zero_failures, trials_needed_for_zero_failures

HERE = os.path.dirname(__file__)


class TestCP(unittest.TestCase):
    def test_known_intervals(self):
        lo, hi = clopper_pearson(5, 10)
        self.assertAlmostEqual(lo, 0.1871, places=3)
        self.assertAlmostEqual(hi, 0.8129, places=3)
        lo, hi = clopper_pearson(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.3085, places=3)
        lo, hi = clopper_pearson(10, 10)
        self.assertEqual(hi, 1.0)
        self.assertAlmostEqual(lo, 0.6915, places=3)

    def test_zero_of_150_two_sided(self):
        _, hi = clopper_pearson(0, 150)
        self.assertAlmostEqual(hi, 0.0243, places=3)
        self.assertAlmostEqual(hi, upper_bound_zero_failures(150, two_sided=True), places=6)

    def test_one_sided_and_sample_size(self):
        self.assertAlmostEqual(upper_bound_zero_failures(100), 0.0295, places=3)
        self.assertEqual(trials_needed_for_zero_failures(0.01), 299)

    def test_contains_point_estimate_and_ordered(self):
        for k, n in [(1, 50), (7, 100), (50, 1000), (3, 100000)]:
            lo, hi = clopper_pearson(k, n)
            self.assertTrue(lo <= k / n <= hi)

    def test_bad_input(self):
        for k, n in [(-1, 5), (6, 5), (0, 0)]:
            with self.assertRaises(ValueError):
                clopper_pearson(k, n)


class TestGate(unittest.TestCase):
    base = {"hard_negative_pairs": 150, "hard_negative_false_merges": 0, "missing_attr_cases": 80,
            "missing_attr_routed_ok": 80, "low_ocr_in_tier1": 0, "mtc_conforms_unverified": 0,
            "auto_tier_tp": 398, "auto_tier_fp": 1, "precision_target": 0.995}

    def run_gate(self, m):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(m, f)
        try:
            return subprocess.run([sys.executable, os.path.join(HERE, "gate_check.py"), f.name],
                                  capture_output=True, text=True)
        finally:
            os.unlink(f.name)

    def test_pass(self):
        r = self.run_gate(self.base)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("GATE: PASS", r.stdout)

    def test_each_gate_can_fail(self):
        for key, val in [("hard_negative_false_merges", 1), ("missing_attr_routed_ok", 79),
                         ("low_ocr_in_tier1", 1), ("mtc_conforms_unverified", 1), ("auto_tier_fp", 10)]:
            m = dict(self.base); m[key] = val
            r = self.run_gate(m)
            self.assertEqual(r.returncode, 1, (key, r.stdout))
            self.assertIn("FAIL", r.stdout)


if __name__ == "__main__":
    unittest.main()
