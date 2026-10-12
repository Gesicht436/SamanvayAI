"""Tests for attribute extractors (ExtractedValue, LexiconExtractor, Size NB, Pressure Class).

Follows standard library and test contract requirements.
"""

import tempfile
from pathlib import Path

from api.extractors.base import ExtractedValue, none_with
from api.extractors.lexicon import LexiconExtractor
from api.extractors.parsers.pressure_class import extract_pressure_class
from api.extractors.parsers.size_nb import extract_size_nb

SAMPLE_LEXICON_TOML = """
attribute = "body_material"
categories = ["VALVES", "FLANGES"]

[values.A216_WCB]
synonyms = ["WCB", "A216 WCB", "ASTM A216 GR WCB"]

[values.A351_CF8M]
synonyms = ["CF8M", "A351 CF8M"]
"""


def test_extracted_value_contract():
    """Verify ExtractedValue dataclass behavior and evidence synchronization."""
    ev = ExtractedValue(value="TEST_VAL", confidence=0.95, evidence_span=(5, 10))
    assert ev.value == "TEST_VAL"
    assert ev.confidence == 0.95
    assert ev.evidence_span == (5, 10)
    assert ev.evidence == (5, 10)
    assert ev.is_valid() is True

    # Test none_with constructor
    conflict = none_with("EXTRACTION_CONFLICT", (2, 8))
    assert conflict.value is None
    assert conflict.confidence == 0.0
    assert conflict.flags == ["EXTRACTION_CONFLICT"]
    assert conflict.evidence_span == (2, 8)
    assert conflict.is_valid() is False


def test_lexicon_extractor_longest_match_and_conflict():
    """Verify longest synonym preference, conflict detection, and evidence spans."""
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
        f.write(SAMPLE_LEXICON_TOML)
        temp_path = f.name

    try:
        extractor = LexiconExtractor(temp_path)

        # Longest match wins
        res1 = extractor.extract("GATE VALVE ASTM A216 GR WCB FLG", "VALVES")
        assert res1.value == "A216_WCB"
        assert res1.confidence == 0.95
        span1 = res1.evidence_span
        assert span1 is not None
        assert "GATE VALVE ASTM A216 GR WCB FLG"[span1[0] : span1[1]] == "ASTM A216 GR WCB"

        # Shorter match
        res2 = extractor.extract("VALVE WCB BODY", "VALVES")
        assert res2.value == "A216_WCB"

        # Conflict when two distinct canonical values are present
        res_conflict = extractor.extract("BODY WCB TRIM CF8M", "VALVES")
        assert res_conflict.value is None
        assert res_conflict.flags == ["EXTRACTION_CONFLICT"]

        # Category gating
        res_disallowed = extractor.extract("VALVE WCB", "CABLES")
        assert res_disallowed.value is None

        # Token boundaries: PREWCB123 should not match
        res_boundary = extractor.extract("VALVE PREWCB123", "VALVES")
        assert res_boundary.value is None
    finally:
        Path(temp_path).unlink(missing_ok=True)


PRESSURE_TEST_CASES = [
    # text, category, expected value, expected flags
    ('GATE VALVE 4" CL150 WCB', "VALVES", "ASME_150", []),
    ("VALVE CLASS 300 RF", "VALVES", "ASME_300", []),
    ("BALL VLV 600# FLG", "VALVES", "ASME_600", []),
    ("FLANGE #900 WN", "FLANGES", "ASME_900", []),
    ("VALVE 150 LBS", "VALVES", "ASME_150", []),
    ("VALVE CL-150", "VALVES", "ASME_150", []),
    ("FLANGE PN16", "FLANGES", "PN_16", []),
    ("FLANGE PN 2.5", "FLANGES", "PN_2.5", []),
    ("VALVE 300 PSI", "VALVES", None, []),  # Bare PSI is not a class
    ("VALVE CLASS 175", "VALVES", None, ["NON_STANDARD_RATING"]),
    ("VALVE CLASS 150/300", "VALVES", None, ["EXTRACTION_CONFLICT"]),
    ("FLANGE CL150 PN16", "FLANGES", None, ["EXTRACTION_CONFLICT"]),
    ("VALVE CL150 150#", "VALVES", "ASME_150", []),  # Same rating repeated is fine
    ("STUD M24X150MM CL150", "FASTENERS", None, []),  # Wrong category
    ("", "VALVES", None, []),
    (None, "VALVES", None, []),
]


def test_pressure_class_extractor_table():
    """Verify pressure class parser against comprehensive golden test cases."""
    for text, category, expected_val, expected_flags in PRESSURE_TEST_CASES:
        res = extract_pressure_class(text, category)
        assert res.value == expected_val, f"Failed on text='{text}', got value='{res.value}'"
        assert res.flags == expected_flags, f"Failed on text='{text}', got flags='{res.flags}'"
        if res.value is None:
            assert res.confidence == 0.0


def test_pressure_class_evidence_span():
    """Verify evidence span indexing into raw text."""
    raw = "gate valve 4in cl150 wcb"
    res = extract_pressure_class(raw, "VALVES")
    assert res.value == "ASME_150"
    s, e = res.evidence_span
    assert raw[s:e] == "150"


SIZE_TEST_CASES = [
    # text, category, expected NB (mm)
    ('GATE VALVE 1-1/2" CL150', "VALVES", 40),
    ("VALVE 1 1/2 INCH", "VALVES", 40),
    ("VALVE DN150 WCB", "VALVES", 150),
    ("PIPE 150NB SMLS", "PIPES", 150),
    ('PIPE SCH 40 6"', "PIPES", 150),  # SCH 40 stripped; 6" gives NB 150
    ("PIPE SCH40 2 INCH", "PIPES", 50),
    ("REDUCER 6X4 INCH", "PIPES", 150),  # Reducer primary size
    ("STUD M24X150MM", "FASTENERS", None),  # Metric fastener rejected
    ("TUBE 60.3 OD X 5.6 WT", "BOILER_TUBE", None),  # Boiler tube rejected
    ("", "VALVES", None),
    (None, "VALVES", None),
]


def test_size_nb_extractor_table():
    """Verify piping size parser against golden test cases."""
    for text, category, expected_nb in SIZE_TEST_CASES:
        res = extract_size_nb(text, category)
        assert res.value == expected_nb, f"Failed on text='{text}', expected={expected_nb}, got={res.value}"


def test_size_nb_evidence_span():
    """Verify evidence span points to raw text."""
    raw = 'pipe sch 40 6" smls'
    res = extract_size_nb(raw, "PIPES")
    assert res.value == 150
    s, e = res.evidence_span
    assert raw[s:e] == "6"


def test_cross_validator_agreement_boosts_confidence():
    """Verify Section 4.3: when Rule and NER agree on HARD attribute, confidence boosts to 0.95+."""
    from api.extractors.cross_validator import cross_validate_attributes

    rule_attrs = {
        "pressure_class": ExtractedValue(value="ASME_150", confidence=0.85, source="rule", evidence_span=(10, 15)),
        "size_nb": ExtractedValue(value=50, confidence=0.90, source="rule", evidence_span=(0, 4)),
    }
    ner_attrs = {
        "pressure_class": ExtractedValue(value="150", confidence=0.88, source="ner", evidence_span=(10, 15)),
        "size_nb": ExtractedValue(value="50", confidence=0.92, source="ner", evidence_span=(0, 4)),
    }

    validated = cross_validate_attributes(
        rule_attrs=rule_attrs,
        aux_attrs=ner_attrs,
        hard_attributes={"pressure_class", "size_nb"},
    )

    assert validated["pressure_class"].value == "ASME_150"
    assert validated["pressure_class"].confidence >= 0.95
    assert validated["pressure_class"].source == "rule+ner"
    assert validated["size_nb"].value == 50
    assert validated["size_nb"].confidence >= 0.95


def test_cross_validator_hard_disagreement_yields_conflict():
    """Verify Section 4.3: when Rule and NER disagree on HARD attribute, value becomes None with EXTRACTION_CONFLICT."""
    from api.extractors.cross_validator import cross_validate_attributes

    rule_attrs = {
        "pressure_class": ExtractedValue(value="ASME_300", confidence=0.85, source="rule", evidence_span=(10, 15)),
    }
    ner_attrs = {
        "pressure_class": ExtractedValue(value="ASME_600", confidence=0.90, source="ner", evidence_span=(20, 25)),
    }

    validated = cross_validate_attributes(
        rule_attrs=rule_attrs,
        aux_attrs=ner_attrs,
        hard_attributes={"pressure_class"},
    )

    res = validated["pressure_class"]
    assert res.value is None
    assert res.confidence == 0.0
    assert "EXTRACTION_CONFLICT" in res.flags
    assert "ATTRIBUTE_EXTRACTION_CONFLICT" in res.flags


def test_cross_validator_s12_statutory_and_hard_invariant():
    """Verify Invariant S12: ML/NER alone cannot infer HARD or statutory attribute without rule backing."""
    from api.extractors.cross_validator import cross_validate_attributes

    rule_attrs = {}
    ner_attrs = {
        "ex_group": ExtractedValue(value="GROUP_I", confidence=0.92, source="ner", evidence_span=(5, 12)),
        "ibr_cert": ExtractedValue(value="IBR_FORM_III", confidence=0.95, source="ner", evidence_span=(20, 30)),
        "paint_shade": ExtractedValue(value="RAL_7035", confidence=0.80, source="ner", evidence_span=(40, 48)),
    }

    validated = cross_validate_attributes(
        rule_attrs=rule_attrs,
        aux_attrs=ner_attrs,
        hard_attributes={"ex_group"},
        statutory_attributes={"ibr_cert"},
    )

    # HARD attribute from NER alone is blocked
    assert validated["ex_group"].value is None
    assert "UNVERIFIED_ML_EXTRACTION" in validated["ex_group"].flags

    # Statutory attribute from NER alone is blocked (Invariant S12)
    assert validated["ibr_cert"].value is None
    assert "S12_STATUTORY_RULE_REQUIRED" in validated["ibr_cert"].flags

    # Soft non-statutory attribute from NER alone is accepted with capped confidence 0.70
    assert validated["paint_shade"].value == "RAL_7035"
    assert validated["paint_shade"].confidence <= 0.70


def test_cross_validator_single_source_rule_and_physical_invalid():
    """Verify single source rule confidence and physical invalid rating handling."""
    from api.extractors.cross_validator import cross_validate_attributes

    rule_attrs = {
        "pressure_class": ExtractedValue(value="ASME_150", confidence=0.80, source="rule"),
        "invalid_attr": ExtractedValue(value="CL175", confidence=0.0, source="rule", flags=["NON_STANDARD_RATING"]),
    }

    validated = cross_validate_attributes(
        rule_attrs=rule_attrs,
        aux_attrs=None,
        hard_attributes={"pressure_class", "invalid_attr"},
    )

    assert validated["pressure_class"].value == "ASME_150"
    assert validated["pressure_class"].confidence == 0.80
    assert validated["invalid_attr"].value is None
    assert "NON_STANDARD_RATING" in validated["invalid_attr"].flags

