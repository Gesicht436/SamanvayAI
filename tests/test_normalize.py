"""Unit tests for text normalization and Indic transliteration engine."""


from api.services.normalize import normalize_text
from api.services.script_detector import detect_scripts


def test_script_detector_latin():
    res = detect_scripts("GATE VALVE 2 INCH 150# RF")
    assert res.primary_script == "Latin"
    assert res.primary_language == "en"
    assert not res.is_mixed_script
    assert "MIXED_SCRIPT" not in res.flags


def test_script_detector_devanagari():
    res = detect_scripts("गेट वाल्व")
    assert res.primary_script == "Devanagari"
    assert res.primary_language == "hi"
    assert not res.is_mixed_script


def test_script_detector_mixed_script():
    res = detect_scripts("वाल्व 2 INCH GATE VALVE")
    assert res.is_mixed_script is True
    assert "MIXED_SCRIPT" in res.flags


def test_quote_standardization():
    raw = "GATE VALVE 2″ 150″ RF ′TEST′ ''DOUBLE''"
    res = normalize_text(raw)
    assert '2"' in res.clean_text
    assert '150"' in res.clean_text
    assert "'TEST'" in res.clean_text
    assert '"DOUBLE"' in res.clean_text


def test_dimension_multiplier_standardization():
    raw = "ANGLE 50 x 50 x 6 MM"
    res = normalize_text(raw)
    assert "50X50X6" in res.clean_text


def test_indic_transliteration_hindi():
    raw = "वाल्व 2″ SS 304 GT #150"
    res = normalize_text(raw, category="VALVES")
    assert res.tokens[0] == "VALVE"
    assert "GATE" in res.tokens
    assert "MIXED_SCRIPT" in res.flags
    assert "UNKNOWN_INDIC_TOKENS" not in res.flags


def test_indic_unknown_tokens():
    # Unknown Hindi word + English
    raw = "अज्ञात 2INCH PIPE"
    res = normalize_text(raw)
    assert "UNKNOWN_INDIC_TOKENS" in res.flags
    assert "अज्ञात" in res.clean_text


def test_category_gated_abbreviations_valves():
    res = normalize_text("GT VALVE GLB CHK", category="VALVES")
    assert "GATE" in res.tokens
    assert "GLOBE" in res.tokens
    assert "CHECK" in res.tokens


def test_category_gated_abbreviations_cables_vs_motors():
    # FR in MOTORS is FRAME
    res_motor = normalize_text("INDUCTION MOTOR FR 132M", category="MOTORS")
    assert "FRAME" in res_motor.tokens
    assert "FLAME RETARDANT" not in res_motor.tokens

    # FR in CABLES is FLAME RETARDANT
    res_cable = normalize_text("COPPER ARMOURED CABLE FR 4CX16", category="CABLES")
    assert "FLAME RETARDANT" in res_cable.clean_text
    assert "FRAME" not in res_cable.tokens


def test_fasteners_std_with_bolt_size():
    # STD followed by M16 -> STUD
    res = normalize_text("HEX BOLT STD M16X50", category="FASTENERS")
    assert "STUD" in res.tokens
    assert "AMBIGUOUS_ABBREVIATION" not in res.flags


def test_fasteners_std_without_bolt_size_flags():
    # STD not followed by bolt size -> remains STD with AMBIGUOUS_ABBREVIATION
    res = normalize_text("HEX BOLT STD GRADE 8.8", category="FASTENERS")
    assert "STD" in res.tokens
    assert "STUD" not in res.tokens
    assert "AMBIGUOUS_ABBREVIATION" in res.flags


def test_unexpanded_when_no_category():
    # STD in unknown category is not expanded
    res = normalize_text("STD BOLT ASSEMBLY")
    assert "STD" in res.tokens
    assert "STUD" not in res.tokens
    assert "STANDARD" not in res.tokens


def test_collision_tokens_preserved():
    # Cross-sector tokens: ROLL, BELT, ST, EP, T22, TUBE, I, R, FC must not be naively expanded
    res = normalize_text("ROLL BELT ST EP T22 TUBE I R FC")
    tokens_set = set(res.tokens)
    assert "ROLL" in tokens_set
    assert "BELT" in tokens_set
    assert "ST" in tokens_set
    assert "EP" in tokens_set
    assert "T22" in tokens_set
    assert "TUBE" in tokens_set
    assert "I" in tokens_set
    assert "R" in tokens_set
    assert "FC" in tokens_set
