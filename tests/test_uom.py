"""Unit tests for Canonical Unit of Measure (UoM) Engine."""

import pytest

from api.services.uom import (
    convert_to_canonical,
    standardize_uom,
)


def test_standardize_uom_aliases():
    assert standardize_uom("NOS")[0] == "EA"
    assert standardize_uom("pcs")[0] == "EA"
    assert standardize_uom("MTR")[0] == "M"
    assert standardize_uom("meters")[0] == "M"
    assert standardize_uom("tonnes")[0] == "MT"
    assert standardize_uom("kgs")[0] == "KG"
    assert standardize_uom("100EA")[0] == "100EA"


def test_standardize_uom_unknown():
    std, flags = standardize_uom("QUINTAL")
    assert std == "QUINTAL"
    assert "UNKNOWN_UOM" in flags


def test_scalar_conversions():
    # KM -> M
    res_km = convert_to_canonical(2.5, "KM")
    assert res_km.canonical_qty == 2500.0
    assert res_km.canonical_uom == "M"

    # FT -> M
    res_ft = convert_to_canonical(100, "FT")
    assert pytest.approx(res_ft.canonical_qty, 0.01) == 30.48
    assert res_ft.canonical_uom == "M"

    # KG -> MT
    res_kg = convert_to_canonical(5000, "KG")
    assert res_kg.canonical_qty == 5.0
    assert res_kg.canonical_uom == "MT"

    # 100EA -> EA
    res_hundred = convert_to_canonical(3, "100EA")
    assert res_hundred.canonical_qty == 300.0
    assert res_hundred.canonical_uom == "EA"


def test_rebar_conversion_with_diameter():
    # 1000m of 12mm rebar: kg/m = 144 / 162 = 0.888889 kg/m -> 0.888889 MT
    res = convert_to_canonical(1000, "M", category="REBAR", attributes={"diameter_mm": 12})
    assert pytest.approx(res.canonical_qty, 0.0001) == 0.888889
    assert res.canonical_uom == "MT"
    assert "MISSING_CONVERSION_ATTRIBUTE" not in res.flags


def test_rebar_conversion_missing_diameter():
    # Safety Invariant: Never guess missing physical attributes!
    res = convert_to_canonical(1000, "M", category="REBAR")
    assert res.canonical_qty == 1000.0
    assert res.canonical_uom == "M"
    assert "MISSING_CONVERSION_ATTRIBUTE" in res.flags


def test_section_conversion_ismb_300():
    # ISMB 300 has 46.0 kg/m in IS 808
    # 100m -> 4600 kg -> 4.6 MT
    res = convert_to_canonical(100, "M", category="SECTIONS", attributes={"designation": "ISMB 300"})
    assert res.canonical_qty == 4.6
    assert res.canonical_uom == "MT"
    assert "MISSING_CONVERSION_ATTRIBUTE" not in res.flags


def test_section_conversion_unknown_profile():
    res = convert_to_canonical(100, "M", category="SECTIONS", attributes={"designation": "NONEXISTENT_BEAM"})
    assert res.canonical_qty == 100.0
    assert "MISSING_CONVERSION_ATTRIBUTE" in res.flags


def test_plate_conversion_with_dimensions():
    # Plate: t=10mm, w=2m, l=5m, count=4
    # Mass per plate = 10 * 2 * 5 * 7.85 = 785 kg
    # 4 plates = 3140 kg = 3.14 MT
    attrs = {"thickness_mm": 10, "width_m": 2, "length_m": 5}
    res = convert_to_canonical(4, "EA", category="PLATES", attributes=attrs)
    assert pytest.approx(res.canonical_qty, 0.01) == 3.14
    assert res.canonical_uom == "MT"
    assert "MISSING_CONVERSION_ATTRIBUTE" not in res.flags


def test_plate_conversion_missing_dimensions():
    res = convert_to_canonical(4, "EA", category="PLATES", attributes={"thickness_mm": 10})
    assert res.canonical_qty == 4.0
    assert "MISSING_CONVERSION_ATTRIBUTE" in res.flags


def test_pipe_weight_to_length_conversion():
    # Pipe: OD=114.3mm, WT=6.02mm (approx 4" Sch 40)
    # kg/m = (114.3 - 6.02) * 6.02 * 0.02466 = 16.075 kg/m
    # 16075 kg (16.075 MT) -> 1000 meters
    attrs = {"od_mm": 114.3, "wt_mm": 6.02}
    res = convert_to_canonical(16.075, "MT", category="PIPES", attributes=attrs)
    assert pytest.approx(res.canonical_qty, 0.5) == 1000.0
    assert res.canonical_uom == "M"


def test_fastener_set_requires_set_definition():
    res = convert_to_canonical(50, "SET", category="FASTENERS")
    assert "MISSING_CONVERSION_ATTRIBUTE" in res.flags
