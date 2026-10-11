"""Specification Registry and extraction orchestrator for Samanvay.

Loads sector pack specifications and lexicons from YAML and TOML, validates schemas,
enforces identity modes and category gating, and dispatches extraction to parsers.
"""

import tomllib
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.extractors.base import ExtractedValue
from api.extractors.lexicon import LexiconExtractor
from api.extractors.parsers import (
    extract_bearing_base_designation,
    extract_bearing_cage,
    extract_bearing_type,
    extract_belt_cover_thickness,
    extract_belt_ply_count,
    extract_belt_strength_class,
    extract_belt_width_mm,
    extract_boiler_tube_ibr,
    extract_boiler_tube_material_spec,
    extract_boiler_tube_od,
    extract_boiler_tube_route,
    extract_boiler_tube_spec_body,
    extract_boiler_tube_wall,
    extract_boiler_tube_wall_basis,
    extract_breaker_breaking_ka,
    extract_breaker_current,
    extract_breaker_duration_s,
    extract_breaker_mounting,
    extract_breaker_poles,
    extract_breaker_voltage,
    extract_cable_conductor_size,
    extract_cable_core_count,
    extract_cable_voltage,
    extract_drawing_item_name,
    extract_drawing_material_grade,
    extract_drawing_number,
    extract_drawing_owner,
    extract_drawing_revision,
    extract_fastener_length,
    extract_fastener_thread_size,
    extract_fastener_type,
    extract_hose_dash_size,
    extract_hose_dn_mm,
    extract_hose_working_pressure_bar,
    extract_instrument_process_conn,
    extract_instrument_range_max,
    extract_instrument_range_min,
    extract_instrument_range_unit,
    extract_mill_roll_barrel_dia,
    extract_mill_roll_barrel_length,
    extract_mill_roll_drawing_number,
    extract_mill_roll_drawing_owner,
    extract_mill_roll_hardness,
    extract_mill_roll_revision,
    extract_motor_efficiency,
    extract_motor_epl,
    extract_motor_ex_groups,
    extract_motor_ex_type,
    extract_motor_frame,
    extract_motor_frequency,
    extract_motor_gas_group,
    extract_motor_poles,
    extract_motor_power,
    extract_motor_speed,
    extract_motor_statutory,
    extract_motor_temp_class,
    extract_motor_voltage,
    extract_otr_construction,
    extract_otr_ply_rating,
    extract_otr_rim_diameter,
    extract_otr_section_width,
    extract_otr_star_rating,
    extract_otr_tread_code,
    extract_pressure_class,
    extract_pump_design_standard,
    extract_pump_discharge_nb,
    extract_pump_driver_kw,
    extract_pump_flange_class,
    extract_pump_flow,
    extract_pump_head,
    extract_pump_impeller_dia,
    extract_pump_seal_plan,
    extract_pump_speed,
    extract_pump_suction_nb,
    extract_pump_type,
    extract_rebar_diameter,
    extract_refractory_bulk_density,
    extract_refractory_chemistry,
    extract_refractory_dimensions,
    extract_refractory_material_class,
    extract_refractory_service_temp,
    extract_refractory_shelf_life,
    extract_size_nb,
    extract_structural_designation,
    extract_structural_profile,
    extract_transformer_cooling,
    extract_transformer_frequency,
    extract_transformer_hv,
    extract_transformer_impedance,
    extract_transformer_lv,
    extract_transformer_phases,
    extract_transformer_rating,
    extract_transformer_rating_max,
    extract_transformer_tap_changer,
    extract_transformer_vector_group,
    extract_wire_rope_approval,
    extract_wire_rope_construction,
    extract_wire_rope_diameter_mm,
    extract_wire_rope_tensile_grade,
)
from api.models.entities import AttributeSpec, SubcategorySpec


class AttributeRole(str, Enum):
    """Attribute matching role defining safety invariant behavior."""

    HARD = "HARD"
    REQUIRED = "REQUIRED"
    SOFT = "SOFT"
    DIRECTIONAL = "DIRECTIONAL"


class IdentityMode(str, Enum):
    """Harmonization identity mode for a subcategory."""

    PARAMETRIC = "PARAMETRIC"
    OEM_PN = "OEM_PN"
    DRAWING = "DRAWING"


class PrimaryDimensionDef(BaseModel):
    """Primary physical dimension definition used for candidate block keys."""

    attr: str
    unit: str


class AttributeSpecDef(BaseModel):
    """Specification of an attribute within a subcategory."""

    name: str
    role: AttributeRole
    when: str | None = None
    statutory: bool = False
    order_def: dict[str, Any] | None = None


class LifeDef(BaseModel):
    """Shelf life and operational life tracking specification."""

    basis: str
    value: int | float | None = None
    source: str | None = None


class SubcategorySpecDef(BaseModel):
    """Complete specification definition for an item subcategory."""

    subcategory: str
    segment: list[str] = Field(default_factory=list)
    identity_mode: IdentityMode = IdentityMode.PARAMETRIC
    safety_critical: bool = False
    expiry_required: bool = False
    pooling_class: str | None = None
    depth: str | None = "standard"
    primary_dimension: PrimaryDimensionDef | None = None
    attributes: list[AttributeSpecDef] = Field(default_factory=list)
    life: list[LifeDef] | None = None


class SpecRegistry:
    """Central registry of subcategory specifications, lexicons, and parsers."""

    def __init__(self) -> None:
        self._specs: dict[str, SubcategorySpecDef] = {}
        self._lexicons: dict[str, list[LexiconExtractor]] = {}  # attr_name -> list of extractors
        self._python_parsers: dict[str, Callable[[str, str | None], ExtractedValue]] = {}
        self._register_default_parsers()

    def _register_default_parsers(self) -> None:
        """Registers core Python parsers for physical attributes across all deep families."""
        # Core physical parsers
        self.register_parser("size_nb", extract_size_nb)
        self.register_parser("pressure_class", extract_pressure_class)

        # Motors (MOTORS.EX)
        self.register_parser("power_kw", extract_motor_power)
        self.register_parser("poles", extract_motor_poles)
        self.register_parser("frame", extract_motor_frame)
        self.register_parser("efficiency_class", extract_motor_efficiency)
        self.register_parser("speed_rpm", extract_motor_speed)
        self.register_parser("voltage_v", extract_motor_voltage)
        self.register_parser("frequency_hz", extract_motor_frequency)
        self.register_parser("ex_type", extract_motor_ex_type)
        self.register_parser("ex_groups", extract_motor_ex_groups)
        self.register_parser("gas_group", extract_motor_gas_group)
        self.register_parser("temp_class", extract_motor_temp_class)
        self.register_parser("epl", extract_motor_epl)
        self.register_parser("statutory_approval_no", extract_motor_statutory)

        # Transformers (POWER.TRANSFORMER)
        self.register_parser("rating_kva", extract_transformer_rating)
        self.register_parser("rating_kva_max", extract_transformer_rating_max)
        self.register_parser("hv_kv", extract_transformer_hv)
        self.register_parser("lv_kv", extract_transformer_lv)
        self.register_parser("vector_group", extract_transformer_vector_group)
        self.register_parser("cooling", extract_transformer_cooling)
        self.register_parser("tap_changer", extract_transformer_tap_changer)
        self.register_parser("impedance_pct", extract_transformer_impedance)
        self.register_parser("phases", extract_transformer_phases)
        self.register_parser("POWER.TRANSFORMER.frequency_hz", extract_transformer_frequency)

        # Refractories (STEEL.REFRACTORY)
        self.register_parser("STEEL.REFRACTORY.material_class", extract_refractory_material_class)
        self.register_parser("dimensions_mm", extract_refractory_dimensions)
        self.register_parser("key_chemistry", extract_refractory_chemistry)
        self.register_parser("shelf_life_days", extract_refractory_shelf_life)
        self.register_parser("bulk_density", extract_refractory_bulk_density)
        self.register_parser("max_service_c", extract_refractory_service_temp)

        # OTR Tyres (MINING.OTR_TYRE)
        self.register_parser("section_width", extract_otr_section_width)
        self.register_parser("construction", extract_otr_construction)
        self.register_parser("rim_diameter_in", extract_otr_rim_diameter)
        self.register_parser("tread_code", extract_otr_tread_code)
        self.register_parser("star_rating", extract_otr_star_rating)
        self.register_parser("ply_rating", extract_otr_ply_rating)

        # Centrifugal Pumps (HEAVY.PUMP_CENTRIFUGAL)
        self.register_parser("flow_m3h", extract_pump_flow)
        self.register_parser("head_m", extract_pump_head)
        self.register_parser("HEAVY.PUMP_CENTRIFUGAL.speed_rpm", extract_pump_speed)
        self.register_parser("pump_type", extract_pump_type)
        self.register_parser("HEAVY.PUMP_CENTRIFUGAL.design_standard", extract_pump_design_standard)
        self.register_parser("suction_nb", extract_pump_suction_nb)
        self.register_parser("discharge_nb", extract_pump_discharge_nb)
        self.register_parser("flange_class", extract_pump_flange_class)
        self.register_parser("impeller_dia_mm", extract_pump_impeller_dia)
        self.register_parser("driver_kw", extract_pump_driver_kw)
        self.register_parser("seal_plan", extract_pump_seal_plan)

        # Cables (CABLES.POWER)
        self.register_parser("CABLES.POWER.voltage_kv", extract_cable_voltage)
        self.register_parser("CABLES.POWER.core_count", extract_cable_core_count)
        self.register_parser("CABLES.POWER.conductor_size_sqmm", extract_cable_conductor_size)

        # Structural Steel (STEEL.STRUCTURAL)
        self.register_parser("STEEL.STRUCTURAL.section_designation", extract_structural_designation)
        self.register_parser("STEEL.STRUCTURAL.profile_type", extract_structural_profile)

        # Rebar (STEEL.REBAR)
        self.register_parser("STEEL.REBAR.diameter_mm", extract_rebar_diameter)

        # Bearings (BEARINGS.BEARING)
        self.register_parser("BEARINGS.BEARING.base_designation", extract_bearing_base_designation)
        self.register_parser("BEARINGS.BEARING.bearing_type", extract_bearing_type)
        self.register_parser("BEARINGS.BEARING.cage_material", extract_bearing_cage)

        # Fasteners (FASTENERS.STUD_BOLT)
        self.register_parser("FASTENERS.STUD_BOLT.thread_size", extract_fastener_thread_size)
        self.register_parser("FASTENERS.STUD_BOLT.length_mm", extract_fastener_length)
        self.register_parser("FASTENERS.STUD_BOLT.fastener_type", extract_fastener_type)

        # Instrumentation (INSTRUMENTS.TRANSMITTER)
        self.register_parser("INSTRUMENTS.TRANSMITTER.range_max", extract_instrument_range_max)
        self.register_parser("INSTRUMENTS.TRANSMITTER.range_min", extract_instrument_range_min)
        self.register_parser("INSTRUMENTS.TRANSMITTER.range_unit", extract_instrument_range_unit)
        self.register_parser("INSTRUMENTS.TRANSMITTER.process_connection", extract_instrument_process_conn)

        # Circuit Breakers (POWER.BREAKER)
        self.register_parser("POWER.BREAKER.voltage_kv", extract_breaker_voltage)
        self.register_parser("POWER.BREAKER.current_a", extract_breaker_current)
        self.register_parser("POWER.BREAKER.breaking_ka", extract_breaker_breaking_ka)
        self.register_parser("POWER.BREAKER.duration_s", extract_breaker_duration_s)
        self.register_parser("POWER.BREAKER.poles", extract_breaker_poles)
        self.register_parser("POWER.BREAKER.mounting", extract_breaker_mounting)

        # Boiler Tubes (POWER.BOILER_TUBE)
        self.register_parser("POWER.BOILER_TUBE.od_mm", extract_boiler_tube_od)
        self.register_parser("POWER.BOILER_TUBE.wall_mm", extract_boiler_tube_wall)
        self.register_parser("POWER.BOILER_TUBE.wall_basis", extract_boiler_tube_wall_basis)
        self.register_parser("POWER.BOILER_TUBE.material_spec", extract_boiler_tube_material_spec)
        self.register_parser("POWER.BOILER_TUBE.manufacturing_route", extract_boiler_tube_route)
        self.register_parser("POWER.BOILER_TUBE.spec_body", extract_boiler_tube_spec_body)
        self.register_parser("POWER.BOILER_TUBE.ibr_cert", extract_boiler_tube_ibr)

        # Conveyor Belts (STEEL.CONVEYOR_BELT)
        self.register_parser("STEEL.CONVEYOR_BELT.strength_class", extract_belt_strength_class)
        self.register_parser("STEEL.CONVEYOR_BELT.ply_count", extract_belt_ply_count)
        self.register_parser("STEEL.CONVEYOR_BELT.belt_width_mm", extract_belt_width_mm)
        self.register_parser("STEEL.CONVEYOR_BELT.cover_thickness", extract_belt_cover_thickness)

        # Mill Rolls (STEEL.MILL_ROLL)
        self.register_parser("STEEL.MILL_ROLL.drawing_number", extract_mill_roll_drawing_number)
        self.register_parser("STEEL.MILL_ROLL.drawing_owner", extract_mill_roll_drawing_owner)
        self.register_parser("STEEL.MILL_ROLL.barrel_diameter_mm", extract_mill_roll_barrel_dia)
        self.register_parser("STEEL.MILL_ROLL.barrel_length_mm", extract_mill_roll_barrel_length)
        self.register_parser("STEEL.MILL_ROLL.drawing_revision", extract_mill_roll_revision)
        self.register_parser("STEEL.MILL_ROLL.hardness", extract_mill_roll_hardness)

        # Wire Ropes (MINING.WIRE_ROPE)
        self.register_parser("MINING.WIRE_ROPE.diameter_mm", extract_wire_rope_diameter_mm)
        self.register_parser("MINING.WIRE_ROPE.construction", extract_wire_rope_construction)
        self.register_parser("MINING.WIRE_ROPE.tensile_grade_mpa", extract_wire_rope_tensile_grade)
        self.register_parser("MINING.WIRE_ROPE.approval_type", extract_wire_rope_approval)

        # Hydraulic Hoses (HEAVY.HYDRAULIC_HOSE)
        self.register_parser("HEAVY.HYDRAULIC_HOSE.dash_size", extract_hose_dash_size)
        self.register_parser("HEAVY.HYDRAULIC_HOSE.dn_mm", extract_hose_dn_mm)
        self.register_parser("HEAVY.HYDRAULIC_HOSE.working_pressure_bar", extract_hose_working_pressure_bar)

        # Made to Drawing (HEAVY.MADE_TO_DRAWING)
        self.register_parser("HEAVY.MADE_TO_DRAWING.drawing_number", extract_drawing_number)
        self.register_parser("HEAVY.MADE_TO_DRAWING.drawing_owner", extract_drawing_owner)
        self.register_parser("HEAVY.MADE_TO_DRAWING.drawing_revision", extract_drawing_revision)
        self.register_parser("HEAVY.MADE_TO_DRAWING.material_grade", extract_drawing_material_grade)
        self.register_parser("HEAVY.MADE_TO_DRAWING.item_name", extract_drawing_item_name)

    def register_parser(
        self,
        attr_name: str,
        parser_fn: Callable[[str, str | None], ExtractedValue],
    ) -> None:
        """Registers a custom Python parser function for an attribute."""
        self._python_parsers[attr_name] = parser_fn

    def clear(self) -> None:
        """Clears all loaded specifications and lexicons (used in testing)."""
        self._specs.clear()
        self._lexicons.clear()
        self._python_parsers.clear()
        self._register_default_parsers()

    def load_spec_file(self, path: str | Path) -> SubcategorySpecDef:
        """Loads and validates a single specification file (.yaml, .yml, or .toml)."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Spec file not found: {file_path}")

        raw_data: dict[str, Any]
        suffix = file_path.suffix.lower()
        if suffix in (".yaml", ".yml"):
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f) or {}
        elif suffix == ".toml":
            with open(file_path, "rb") as f:
                raw_data = tomllib.load(f)
        else:
            raise ValueError(f"Unsupported spec format: {file_path}")

        spec = SubcategorySpecDef.model_validate(raw_data)
        self._specs[spec.subcategory] = spec
        return spec

    def load_lexicon_file(self, path: str | Path) -> LexiconExtractor:
        """Loads a single lexicon file and registers it."""
        extractor = LexiconExtractor(path)
        attr = extractor.attribute
        if attr not in self._lexicons:
            self._lexicons[attr] = []
        self._lexicons[attr].append(extractor)
        return extractor

    def load_packs(self, root_dir: str | Path = "packs") -> int:
        """Scans and loads all sector packs from the specified directory.

        Finds:
        - `packs/<pack>/specs/*.yaml` and `*.toml`
        - `packs/<pack>/lexicons/*.toml` and `*.yaml`

        Returns:
            Total number of subcategory specifications loaded.
        """
        packs_path = Path(root_dir)
        if not packs_path.exists():
            return 0

        count = 0
        pack_dirs = (
            [packs_path] if (packs_path / "specs").exists() else [p for p in sorted(packs_path.iterdir()) if p.is_dir()]
        )
        for pack_dir in pack_dirs:
            # Load specifications
            specs_dir = pack_dir / "specs"
            if specs_dir.exists() and specs_dir.is_dir():
                for spec_file in sorted(specs_dir.iterdir()):
                    if spec_file.suffix.lower() in (".yaml", ".yml", ".toml"):
                        self.load_spec_file(spec_file)
                        count += 1

            # Load lexicons
            lex_dir = pack_dir / "lexicons"
            if lex_dir.exists() and lex_dir.is_dir():
                for lex_file in sorted(lex_dir.iterdir()):
                    if lex_file.suffix.lower() in (".yaml", ".yml", ".toml"):
                        self.load_lexicon_file(lex_file)

        return count

    def get_spec(self, subcategory: str) -> SubcategorySpecDef | None:
        """Returns the specification for a subcategory, if registered."""
        return self._specs.get(subcategory)

    def list_subcategories(self) -> list[str]:
        """Returns sorted list of registered subcategory codes."""
        return sorted(self._specs.keys())

    def get_identity_mode(self, subcategory: str) -> IdentityMode:
        """Returns identity mode of subcategory, defaulting to PARAMETRIC."""
        spec = self.get_spec(subcategory)
        return spec.identity_mode if spec else IdentityMode.PARAMETRIC

    def get_hard_attributes(self, subcategory: str) -> list[str]:
        """Returns list of HARD attribute names for a subcategory."""
        spec = self.get_spec(subcategory)
        if not spec:
            return []
        return [attr.name for attr in spec.attributes if attr.role == AttributeRole.HARD]

    def get_required_attributes(self, subcategory: str) -> list[str]:
        """Returns list of REQUIRED attribute names for a subcategory."""
        spec = self.get_spec(subcategory)
        if not spec:
            return []
        return [attr.name for attr in spec.attributes if attr.role == AttributeRole.REQUIRED]

    def extract_attributes(self, text: str, subcategory: str) -> dict[str, ExtractedValue]:
        """Extracts all attributes configured for a given subcategory.

        Priority order per attribute:
        1. Dedicated Python parser if registered.
        2. Lexicon extractor if registered.
        3. Empty ExtractedValue if no extractor exists.
        """
        spec = self.get_spec(subcategory)
        if not spec:
            return {}

        results: dict[str, ExtractedValue] = {}
        for attr_def in spec.attributes:
            name = attr_def.name

            # Check dedicated Python parser (qualified name first, then generic)
            qualified_key = f"{subcategory}.{name}"
            if qualified_key in self._python_parsers:
                parser_fn = self._python_parsers[qualified_key]
                extracted = parser_fn(text, subcategory)
                results[name] = extracted
                continue
            elif name in self._python_parsers:
                parser_fn = self._python_parsers[name]
                extracted = parser_fn(text, subcategory)
                results[name] = extracted
                continue

            # Check lexicon extractors
            if name in self._lexicons:
                chosen = ExtractedValue()
                for lex in self._lexicons[name]:
                    val = lex.extract(text, subcategory)
                    if val.value is not None or len(val.flags) > 0:
                        chosen = val
                        break
                results[name] = chosen
                continue

            # Unparsed attribute defaults to empty
            results[name] = ExtractedValue()

        return results

    async def sync_to_db(self, session: AsyncSession) -> tuple[int, int]:
        """Upserts all in-memory specifications into PostgreSQL database tables.

        Returns:
            Tuple of (subcategories_synced, attributes_synced).
        """
        sub_count = 0
        attr_count = 0

        for spec in self._specs.values():
            sub_entity = await session.get(SubcategorySpec, spec.subcategory)
            if not sub_entity:
                sub_entity = SubcategorySpec(subcategory=spec.subcategory)
                session.add(sub_entity)

            sub_entity.segment = spec.segment
            sub_entity.identity_mode = spec.identity_mode.value
            sub_entity.safety_critical = spec.safety_critical
            sub_entity.expiry_required = spec.expiry_required
            sub_entity.pooling_class = spec.pooling_class
            sub_entity.depth = spec.depth
            sub_count += 1

            for a in spec.attributes:
                attr_entity = await session.get(AttributeSpec, (spec.subcategory, a.name))
                if not attr_entity:
                    attr_entity = AttributeSpec(subcategory=spec.subcategory, attr=a.name)
                    session.add(attr_entity)

                attr_entity.role = a.role.value
                attr_entity.condition_expr = a.when
                attr_entity.order_def = a.order_def
                attr_entity.statutory = a.statutory
                attr_count += 1

        await session.commit()
        return sub_count, attr_count


# Global singleton registry instance
default_registry = SpecRegistry()
