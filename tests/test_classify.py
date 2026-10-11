"""Unit tests for the Subcategory Classifier service."""

import unittest

from api.services.classify import classify_subcategory


class TestSubcategoryClassifier(unittest.TestCase):
    def test_classify_deep_flagship_families(self):
        """Verify classification of the 6 deep flagship families."""
        cases = [
            ("GATE VALVE 100NB CL150 WCB FLANGED RF API600", "VALVES.GATE"),
            ("INDUCTION MOTOR 75 KW 4 POLE 415V FOOT B3 TEFC FLAMEPROOF EX D IIC T4", "MOTORS.EX"),
            ("POWER TRANSFORMER 10 MVA 33/11 KV DYN11 ONAN", "POWER.TRANSFORMER"),
            ("REFRACTORY BRICK MAG-CARBON MGO 97% C 14% 230X114X75 STRAIGHT RESIN", "STEEL.REFRACTORY"),
            ("OTR TYRE 27.00R49 E4 ** TUBELESS 48PR", "MINING.OTR_TYRE"),
            ("CENTRIFUGAL PUMP API 610 OH2 100 M3/HR @ 50 M HEAD 2950 RPM 4X3-10 CL300 S-6", "HEAVY.PUMP_CENTRIFUGAL"),
        ]
        for desc, expected_sub in cases:
            res = classify_subcategory(desc)
            self.assertEqual(res.subcategory, expected_sub, f"Failed for {desc}")
            self.assertGreaterEqual(res.confidence, 0.90)
            self.assertNotIn("CATEGORY_UNCERTAIN", res.flags)

    def test_classify_standard_families(self):
        """Verify classification of standard domain families."""
        cases = [
            ("SEAMLESS PIPE 200 NB SCH 40 ASTM A106 GR B BE", "PIPES.PIPE"),
            ("FLANGE WNRF 150 NB CL300 A105 SCH 40 RF ASME B16.5", "FLANGES.FLANGE"),
            ("POWER CABLE 1.1KV 4C X 16 SQMM AL XLPE ARMOURED", "CABLES.POWER"),
            ("STEEL BEAM ISMB 300 GRADE E250A LENGTH 12M", "STEEL.STRUCTURAL"),
            ("TMT BAR 25MM FE 500D CRS IS 1786", "STEEL.REBAR"),
            ("DEEP GROOVE BALL BEARING 6312 2RS C3", "BEARINGS.BEARING"),
            ("STUD BOLT M24X150MM ASTM A193 B7 WITH 2 NUTS A194 2H", "FASTENERS.STUD_BOLT"),
            ("PRESSURE TRANSMITTER 0-10 BAR 4-20MA HART SS316L 1/2 NPT", "INSTRUMENTS.TRANSMITTER"),
            ("VACUUM CIRCUIT BREAKER 33KV 1250A 25KA 3S VCB", "POWER.BREAKER"),
            ("BOILER TUBE 51.0 OD X 4.5 WT SA213-T22 SEAMLESS IBR", "POWER.BOILER_TUBE"),
            ("CONVEYOR BELT EP 800/4 1400MM 5+2 GRADE M DIN 22102", "STEEL.CONVEYOR_BELT"),
            ("ROLLING MILL ROLL WORK ROLL BARREL 600X1200MM FORGED STEEL DRG 1234", "STEEL.MILL_ROLL"),
            ("STEEL WIRE ROPE 32MM 6X36 IWRC 1960 N/MM2 RHOL BRIGHT", "MINING.WIRE_ROPE"),
            ("HYDRAULIC HOSE 1/2 INCH -8 2SN 275 BAR 1000MM BSP FEMALE SWIVEL", "HEAVY.HYDRAULIC_HOSE"),
            ("FABRICATED COVER PLATE AS PER DRG NO ABC-1234 REV 0 SAIL", "HEAVY.MADE_TO_DRAWING"),
        ]
        for desc, expected_sub in cases:
            res = classify_subcategory(desc)
            self.assertEqual(res.subcategory, expected_sub, f"Failed for {desc}")
            self.assertGreaterEqual(res.confidence, 0.90)

    def test_classify_with_category_hint(self):
        """Category hint guides ambiguous descriptions."""
        res = classify_subcategory("100 NB A106 GR B", category_hint="PIPES")
        self.assertEqual(res.subcategory, "PIPES.PIPE")

        res_valve = classify_subcategory("100 NB FLANGED", category_hint="VALVES.GATE")
        self.assertEqual(res_valve.subcategory, "VALVES.GATE")

    def test_uncertain_and_empty_descriptions(self):
        """Uncertain or empty text sets CATEGORY_UNCERTAIN flag."""
        empty_res = classify_subcategory("")
        self.assertTrue(empty_res.is_uncertain)
        self.assertIn("CATEGORY_UNCERTAIN", empty_res.flags)

        nonsense_res = classify_subcategory("MISCELLANEOUS NONDESCRIPT HARDWARE WIDGET")
        self.assertTrue(nonsense_res.is_uncertain)
        self.assertIn("CATEGORY_UNCERTAIN", nonsense_res.flags)


if __name__ == "__main__":
    unittest.main()
