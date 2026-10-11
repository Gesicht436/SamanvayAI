"""Unit tests for Standard Domain physical attribute parsers.

Covers all 15 standard families across Common, Power, Steel, Mining, and Heavy Engineering.
Conforms to specsheet.md Section 7.5, 18.2, 18.4.2-3, 18.5.2-3, 18.6.2, 18.7.2-3.
"""

from api.extractors.parsers.bearings import (
    extract_bearing_base_designation,
    extract_bearing_cage,
    extract_bearing_type,
)
from api.extractors.parsers.boiler_tubes import (
    extract_boiler_tube_ibr,
    extract_boiler_tube_material_spec,
    extract_boiler_tube_od,
    extract_boiler_tube_spec_body,
    extract_boiler_tube_wall,
    extract_boiler_tube_wall_basis,
)
from api.extractors.parsers.breakers import (
    extract_breaker_breaking_ka,
    extract_breaker_current,
    extract_breaker_duration_s,
    extract_breaker_mounting,
    extract_breaker_poles,
    extract_breaker_voltage,
)
from api.extractors.parsers.cables import (
    extract_cable_conductor_size,
    extract_cable_core_count,
    extract_cable_voltage,
)
from api.extractors.parsers.conveyor_belts import (
    extract_belt_cover_thickness,
    extract_belt_ply_count,
    extract_belt_strength_class,
    extract_belt_width_mm,
)
from api.extractors.parsers.fasteners import (
    extract_fastener_length,
    extract_fastener_thread_size,
    extract_fastener_type,
)
from api.extractors.parsers.hydraulic_hoses import (
    extract_hose_dash_size,
    extract_hose_dn_mm,
    extract_hose_working_pressure_bar,
)
from api.extractors.parsers.instrumentation import (
    extract_instrument_process_conn,
    extract_instrument_range_max,
    extract_instrument_range_min,
    extract_instrument_range_unit,
)
from api.extractors.parsers.made_to_drawing import (
    extract_drawing_item_name,
    extract_drawing_material_grade,
    extract_drawing_number,
    extract_drawing_owner,
    extract_drawing_revision,
)
from api.extractors.parsers.mill_rolls import (
    extract_mill_roll_barrel_dia,
    extract_mill_roll_barrel_length,
    extract_mill_roll_drawing_number,
    extract_mill_roll_drawing_owner,
    extract_mill_roll_hardness,
    extract_mill_roll_revision,
)
from api.extractors.parsers.rebar import extract_rebar_diameter
from api.extractors.parsers.structural import (
    extract_structural_designation,
    extract_structural_profile,
)
from api.extractors.parsers.wire_ropes import (
    extract_wire_rope_approval,
    extract_wire_rope_construction,
    extract_wire_rope_diameter_mm,
    extract_wire_rope_tensile_grade,
)


def test_cables_parser():
    text = "POWER CABLE 1.1KV 3.5C X 240 SQMM AL XLPE ARMOURED"
    assert extract_cable_voltage(text).value == 1.1
    assert extract_cable_core_count(text).value == 3.5
    assert extract_cable_conductor_size(text).value == 240


def test_structural_parser():
    beam = "STRUCTURAL STEEL BEAM ISMB 300 IS 2062 E250A"
    assert extract_structural_designation(beam).value == "ISMB 300"
    assert extract_structural_profile(beam).value == "BEAM"

    chan = "STEEL CHANNEL ISMC 200 IS 2062 E250"
    assert extract_structural_designation(chan).value == "ISMC 200"
    assert extract_structural_profile(chan).value == "CHANNEL"

    angle = "EQUAL ANGLE ISA 75X75X8 IS 2062"
    assert extract_structural_designation(angle).value == "ISA 75X75X8"
    assert extract_structural_profile(angle).value == "ANGLE"


def test_rebar_parser():
    t1 = "TMT REBAR 25MM FE 500D IS 1786"
    assert extract_rebar_diameter(t1).value == 25
    assert len(extract_rebar_diameter(t1).flags) == 0

    t2 = "TMT REBAR 15MM FE 500"  # Non-standard diameter
    assert extract_rebar_diameter(t2).value == 15
    assert "NON_STANDARD_REBAR_DIA" in extract_rebar_diameter(t2).flags


def test_bearings_parser():
    b1 = "BEARING 6312 C3 2RS DEEP GROOVE BALL"
    assert extract_bearing_base_designation(b1).value == "6312"
    assert extract_bearing_type(b1).value == "DEEP_GROOVE_BALL"

    b2 = "BEARING 22212 C3 SPHERICAL ROLLER BRASS CAGE M"
    assert extract_bearing_base_designation(b2).value == "22212"
    assert extract_bearing_type(b2).value == "SPHERICAL_ROLLER"
    assert extract_bearing_cage(b2).value == "BRASS"


def test_fasteners_parser():
    f1 = "STUD BOLT M24X150 WITH 2 HEAVY HEX NUTS ASTM A193 B7"
    assert extract_fastener_thread_size(f1).value == "M24"
    assert extract_fastener_length(f1).value == 150
    assert extract_fastener_type(f1).value == "STUD_BOLT"


def test_instrumentation_parser():
    inst = 'PRESSURE TRANSMITTER 0-10 BAR 4-20MA HART SS316 1/2" NPT(F)'
    assert extract_instrument_range_min(inst).value == 0
    assert extract_instrument_range_max(inst).value == 10
    assert extract_instrument_range_unit(inst).value == "BAR"
    assert extract_instrument_process_conn(inst).value == "1/2_NPT_F"


def test_breakers_parser():
    brk = "VACUUM CIRCUIT BREAKER 11KV 1250A 25KA/3S 3P WITHDRAWABLE"
    assert extract_breaker_voltage(brk).value == 11.0
    assert extract_breaker_current(brk).value == 1250
    assert extract_breaker_breaking_ka(brk).value == 25
    assert extract_breaker_duration_s(brk).value == 3
    assert extract_breaker_poles(brk).value == 3
    assert extract_breaker_mounting(brk).value == "WITHDRAWABLE"


def test_boiler_tubes_parser():
    tube1 = "BOILER TUBE 60.3 OD X 5.6 WT MWT SA213 T22 SEAMLESS IBR"
    assert extract_boiler_tube_od(tube1).value == 60.3
    assert extract_boiler_tube_wall(tube1).value == 5.6
    assert extract_boiler_tube_wall_basis(tube1).value == "MINIMUM"
    assert extract_boiler_tube_material_spec(tube1).value == "SA213"
    assert extract_boiler_tube_spec_body(tube1).value == "ASME_SA"
    assert extract_boiler_tube_ibr(tube1).value == "IBR_FORM_III_A"

    tube2 = "BOILER TUBE 50.8 OD X 4.5 WT SA213 T11"
    # When wall basis is omitted, must flag WALL_BASIS_UNKNOWN
    res_b = extract_boiler_tube_wall_basis(tube2)
    assert "WALL_BASIS_UNKNOWN" in res_b.flags


def test_conveyor_belts_parser():
    cb1 = "CONVEYOR BELT EP 630/4 1200MM 6+3 FRAS"
    assert extract_belt_strength_class(cb1).value == 630
    assert extract_belt_ply_count(cb1).value == 4
    assert extract_belt_width_mm(cb1).value == 1200
    assert extract_belt_cover_thickness(cb1).value == "6+3"

    # Conflicting ply count
    cb2 = "CONVEYOR BELT EP 630/4 1200MM 3 PLY"
    res_ply = extract_belt_ply_count(cb2)
    assert "PLY_CONFLICT" in res_ply.flags


def test_mill_rolls_parser():
    mr = "MILL WORK ROLL 600X1800 MM DRG NO: D-44120 SAIL REV A 70-75 HSC"
    assert extract_mill_roll_drawing_number(mr).value == "D44120"
    assert extract_mill_roll_drawing_owner(mr).value == "SAIL"
    assert extract_mill_roll_barrel_dia(mr).value == 600
    assert extract_mill_roll_barrel_length(mr).value == 1800
    assert extract_mill_roll_revision(mr).value == "REV_A"
    assert extract_mill_roll_hardness(mr).value == "70-75_HSC"


def test_wire_ropes_parser():
    wr = "WIRE ROPE 24MM 6X36 WS IWRC RHOL 1770 GALVANIZED DGMS APPROVED"
    assert extract_wire_rope_diameter_mm(wr).value == 24
    assert extract_wire_rope_construction(wr).value == "6X36 WS"
    assert extract_wire_rope_tensile_grade(wr).value == 1770
    assert extract_wire_rope_approval(wr).value == "DGMS_WINDING"


def test_hydraulic_hoses_parser():
    h1 = "HYDRAULIC HOSE SAE 100R2AT -8 275 BAR JIC 37"
    assert extract_hose_dash_size(h1).value == "-8"
    assert extract_hose_dn_mm(h1).value == 12
    assert extract_hose_working_pressure_bar(h1).value == 275
    assert len(extract_hose_working_pressure_bar(h1).flags) == 0

    # Conflicting working pressure (400 bar stated for 1SN -8 hose where rating is ~160 bar)
    h2 = "HYDRAULIC HOSE SAE 100R1AT -8 400 BAR JIC 37"
    res_p = extract_hose_working_pressure_bar(h2)
    assert "PRESSURE_CONFLICT" in res_p.flags


def test_made_to_drawing_parser():
    drg = "PINION SHAFT DRG NO: D-44120-1 REV A BHEL EN 19"
    assert extract_drawing_number(drg).value == "D44120-1"
    assert extract_drawing_owner(drg).value == "BHEL"
    assert extract_drawing_revision(drg).value == "REV_A"
    assert extract_drawing_material_grade(drg).value == "EN 19"
    assert extract_drawing_item_name(drg).value == "PINION SHAFT"
