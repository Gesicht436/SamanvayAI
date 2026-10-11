"""Unit tests for deep family physical parsers (Motors, Transformers, Refractory, OTR Tyres, Pumps)."""

from api.extractors.parsers.motors import (
    extract_motor_efficiency,
    extract_motor_epl,
    extract_motor_ex_groups,
    extract_motor_ex_type,
    extract_motor_frame,
    extract_motor_gas_group,
    extract_motor_poles,
    extract_motor_power,
    extract_motor_speed,
    extract_motor_temp_class,
)
from api.extractors.parsers.otr_tyres import (
    extract_otr_construction,
    extract_otr_ply_rating,
    extract_otr_rim_diameter,
    extract_otr_section_width,
    extract_otr_star_rating,
    extract_otr_tread_code,
)
from api.extractors.parsers.pumps import (
    extract_pump_discharge_nb,
    extract_pump_flow,
    extract_pump_head,
    extract_pump_suction_nb,
    extract_pump_type,
)
from api.extractors.parsers.refractory import (
    extract_refractory_chemistry,
    extract_refractory_dimensions,
    extract_refractory_shelf_life,
)
from api.extractors.parsers.transformers import (
    extract_transformer_cooling,
    extract_transformer_hv,
    extract_transformer_lv,
    extract_transformer_rating,
    extract_transformer_tap_changer,
    extract_transformer_vector_group,
)


class TestMotorParsers:
    def test_power_conversion_and_snap(self):
        # 75 HP maps to 55 kW
        res = extract_motor_power("INDUCTION MOTOR 75 HP 4P B3")
        assert res.value == 55.0
        assert "NON_STANDARD_RATING" not in res.flags

        # Standard 37 kW
        res = extract_motor_power("MOTOR 37 KW 1480 RPM")
        assert res.value == 37.0

        # Non-standard power rating
        res = extract_motor_power("CUSTOM MOTOR 33.5 KW")
        assert res.value == 33.5
        assert "NON_STANDARD_RATING" in res.flags

    def test_poles_and_speed(self):
        res = extract_motor_poles("MOTOR 45 KW 4 POLE B3")
        assert res.value == 4

        # Infer poles from 1475 RPM
        res = extract_motor_poles("MOTOR 55 KW 1475 RPM B3")
        assert res.value == 4

        # Speed RPM
        res_spd = extract_motor_speed("MOTOR 55 KW 1475 RPM B3")
        assert res_spd.value == 1475

    def test_frame_and_nema_flag(self):
        res_iec = extract_motor_frame("MOTOR 55 KW FRAME 250M B3")
        assert res_iec.value == "250M"
        assert "NEMA_FRAME" not in res_iec.flags

        res_nema = extract_motor_frame("MOTOR 50 HP NEMA 326T FRAME")
        assert res_nema.value == "326T"
        assert "NEMA_FRAME" in res_nema.flags

    def test_ex_markings_group_i_vs_group_ii(self):
        # Surface Group II motor
        text_ii = "MOTOR Ex d IIB T4 Gb"
        assert extract_motor_ex_groups(text_ii).value == "II"
        assert extract_motor_ex_type(text_ii).value == "Ex d"
        assert extract_motor_gas_group(text_ii).value == "IIB"
        assert extract_motor_temp_class(text_ii).value == "T4"
        assert extract_motor_epl(text_ii).value == "Gb"

        # Underground Mining Group I motor (gas group and temp class are None)
        text_i = "MINING MOTOR Ex d I Mb"
        assert extract_motor_ex_groups(text_i).value == "I"
        assert extract_motor_ex_type(text_i).value == "Ex d"
        assert extract_motor_gas_group(text_i).value is None
        assert extract_motor_temp_class(text_i).value is None
        assert extract_motor_epl(text_i).value == "Mb"

    def test_efficiency_classes(self):
        assert extract_motor_efficiency("MOTOR IE3 HIGH EFFICIENCY").value == "IE3"
        assert extract_motor_efficiency("LEGACY MOTOR EFF2").value == "EFF2"


class TestTransformerParsers:
    def test_rating_kva_and_mva(self):
        res = extract_transformer_rating("TRANSFORMER 10 MVA 33/11 KV")
        assert res.value == 10000.0

        res_dual = extract_transformer_rating("TRANSFORMER 20/25 MVA 132/33 KV ONAN/ONAF")
        assert res_dual.value == 20000.0

    def test_voltage_pair_normalization(self):
        text = "POWER TRANSFORMER 33/11 KV 3PH"
        assert extract_transformer_hv(text).value == 33.0
        assert extract_transformer_lv(text).value == 11.0

        text_low = "DISTRIBUTION TRANSFORMER 11KV/415V"
        assert extract_transformer_hv(text_low).value == 11.0
        assert extract_transformer_lv(text_low).value == 0.415

        # Swapped voltage order flag
        text_swap = "STEP UP TRANSFORMER 11/33 KV"
        res_hv = extract_transformer_hv(text_swap)
        assert "VOLTAGE_ORDER_SWAPPED" in res_hv.flags

    def test_vector_group_canonicalization(self):
        assert extract_transformer_vector_group("TRANSFORMER DYN11").value == "Dyn11"
        assert extract_transformer_vector_group("TRANSFORMER DYN-11").value == "Dyn11"
        assert extract_transformer_vector_group("TRANSFORMER YNyn0").value == "YNyn0"
        assert extract_transformer_vector_group("TRANSFORMER YNd1").value == "YNd1"
        # Negative test: DYNAMIC yields nothing
        assert extract_transformer_vector_group("DYNAMIC STABILIZER TRANSFORMER").value is None

    def test_cooling_and_tap_changer(self):
        assert extract_transformer_cooling("TRANSFORMER ONAN/ONAF").value == "ONAN/ONAF"
        assert extract_transformer_tap_changer("TRANSFORMER WITH OLTC").value == "ON_LOAD"
        assert extract_transformer_tap_changer("TRANSFORMER OFF CIRCUIT TAP").value == "OFF_CIRCUIT"


class TestRefractoryParsers:
    def test_dimensions_and_taper(self):
        res = extract_refractory_dimensions("BRICK 230X114X75 MM")
        assert res.value == "230X114X75"

        res_taper = extract_refractory_dimensions("ARCH BRICK 230 X 114 X 75/65")
        assert res_taper.value == "230X114X75/65"

    def test_chemistry(self):
        assert extract_refractory_chemistry("AL2O3 70% MIN BRICK").value == "AL2O3_MIN_70"
        assert extract_refractory_chemistry("MAG-CARBON MGO 97% C 14%").value == "MGO_MIN_97_C_14"

    def test_shelf_life(self):
        assert extract_refractory_shelf_life("CASTABLE 180 DAYS SHELF LIFE").value == 180
        assert extract_refractory_shelf_life("MORTAR 6 MONTHS").value == 180


class TestOTRTyreParsers:
    def test_size_radial_vs_bias(self):
        text_r = "OTR TYRE 27.00R49 E4 **"
        assert extract_otr_section_width(text_r).value == "27.00"
        assert extract_otr_construction(text_r).value == "RADIAL"
        assert extract_otr_rim_diameter(text_r).value == 49

        text_b = "OTR TYRE 27.00-49 E4 BIAS"
        assert extract_otr_construction(text_b).value == "BIAS"

        text_giant = "TYRE 59/80R63 E4"
        assert extract_otr_section_width(text_giant).value == "59/80"
        assert extract_otr_rim_diameter(text_giant).value == 63

    def test_tread_and_stars(self):
        assert extract_otr_tread_code("TYRE 27.00R49 E4").value == "E4"
        assert extract_otr_tread_code("LOADER TYRE L5").value == "L5"
        assert extract_otr_star_rating("TYRE 27.00R49 **").value == "2_STAR"
        assert extract_otr_star_rating("TYRE 27.00R49 2 STAR").value == "2_STAR"
        assert extract_otr_ply_rating("TYRE 27.00-49 48PR").value == "48PR"


class TestPumpParsers:
    def test_flow_conversions(self):
        assert extract_pump_flow("PUMP 100 M3/HR").value == 100.0
        # 25 L/S * 3.6 = 90.0 m3/h
        assert extract_pump_flow("PUMP 25 L/S").value == 90.0
        # 440 GPM * 0.2271247 = 99.93 m3/h
        assert extract_pump_flow("PUMP 440 GPM").value == 99.93

    def test_head_and_pressure_flag(self):
        assert extract_pump_head("PUMP 50 M HEAD").value == 50.0
        # 164 FT * 0.3048 = 49.99 m
        assert extract_pump_head("PUMP 164 FT HEAD").value == 49.99

        # Safety rule: never convert pressure to head
        res_press = extract_pump_head("PUMP 5 BAR HEAD")
        assert res_press.value is None
        assert "PRESSURE_NOT_HEAD" in res_press.flags

    def test_pump_type_and_oem_nozzle_code(self):
        assert extract_pump_type("PUMP API 610 OH2").value == "OH2"
        assert extract_pump_type("PUMP BB2").value == "BB2"

        # 4X3-10 OEM size code -> suction 100 NB, discharge 80 NB
        text_oem = "PUMP 4X3-10 CL300"
        s_res = extract_pump_suction_nb(text_oem)
        d_res = extract_pump_discharge_nb(text_oem)
        assert s_res.value == 100
        assert d_res.value == 80
        assert "OEM_SIZE_CODE" in s_res.flags
