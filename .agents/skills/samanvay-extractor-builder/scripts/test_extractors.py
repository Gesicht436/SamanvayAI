import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(__file__))
from extract_base import LexiconExtractor, load_lexicon
from pressure_class import extract_pressure_class

LEX = '''
attribute = "body_material"
categories = ["VALVES", "FLANGES"]
[values.A216_WCB]
synonyms = ["WCB", "A216 WCB", "ASTM A216 GR WCB"]
[values.A351_CF8M]
synonyms = ["CF8M", "A351 CF8M"]
'''

PRESSURE_CASES = [
    # text, category, expected value, expected flags
    ("GATE VALVE 4\" CL150 WCB", "VALVES", "ASME_150", []),
    ("VALVE CLASS 300 RF", "VALVES", "ASME_300", []),
    ("BALL VLV 600# FLG", "VALVES", "ASME_600", []),
    ("FLANGE #900 WN", "FLANGES", "ASME_900", []),
    ("VALVE 150 LBS", "VALVES", "ASME_150", []),
    ("VALVE CL-150", "VALVES", "ASME_150", []),
    ("FLANGE PN16", "FLANGES", "PN_16", []),
    ("FLANGE PN 2.5", "FLANGES", "PN_2.5", []),
    ("VALVE 300 PSI", "VALVES", None, []),                     # bare PSI is not a class
    ("VALVE CLASS 175", "VALVES", None, ["NON_STANDARD_RATING"]),
    ("VALVE CLASS 150/300", "VALVES", None, ["EXTRACTION_CONFLICT"]),
    ("FLANGE CL150 PN16", "FLANGES", None, ["EXTRACTION_CONFLICT"]),
    ("VALVE CL150 150#", "VALVES", "ASME_150", []),            # same value twice is fine
    ("STUD M24X150MM CL150", "FASTENERS", None, []),           # wrong category
    ("", "VALVES", None, []),
    (None, "VALVES", None, []),
]


class TestPressureClass(unittest.TestCase):
    def test_table(self):
        for text, cat, val, flags in PRESSURE_CASES:
            r = extract_pressure_class(text, cat)
            self.assertEqual(r.value, val, (text, r))
            self.assertEqual(r.flags, flags, (text, r))

    def test_evidence_span_points_at_raw_text(self):
        raw = "gate valve 4in cl150 wcb"
        r = extract_pressure_class(raw, "VALVES")
        s, e = r.evidence
        self.assertEqual(raw[s:e], "150")

    def test_none_never_has_confidence(self):
        for text, cat, val, _ in PRESSURE_CASES:
            r = extract_pressure_class(text, cat)
            if r.value is None:
                self.assertEqual(r.confidence, 0.0)


class TestLexicon(unittest.TestCase):
    def setUp(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(LEX)
        self.ex = LexiconExtractor(load_lexicon(f.name))
        os.unlink(f.name)

    def test_basic_and_longest_wins(self):
        self.assertEqual(self.ex.extract("GATE VALVE ASTM A216 GR WCB", "VALVES").value, "A216_WCB")
        self.assertEqual(self.ex.extract("GATE VALVE A216 WCB", "VALVES").value, "A216_WCB")
        self.assertEqual(self.ex.extract("valve cf8m body", "VALVES").value, "A351_CF8M")

    def test_conflict(self):
        r = self.ex.extract("BODY WCB TRIM CF8M", "VALVES")
        self.assertIsNone(r.value)
        self.assertEqual(r.flags, ["EXTRACTION_CONFLICT"])

    def test_token_boundaries_and_gating(self):
        self.assertIsNone(self.ex.extract("PREWCB123", "VALVES").value)
        self.assertIsNone(self.ex.extract("WCB", "CABLES").value)
        self.assertIsNone(self.ex.extract("", "VALVES").value)

    def test_evidence(self):
        raw = "gate valve wcb"
        r = self.ex.extract(raw, "VALVES")
        self.assertEqual(raw.upper()[r.evidence[0]:r.evidence[1]], "WCB")


if __name__ == "__main__":
    unittest.main()
