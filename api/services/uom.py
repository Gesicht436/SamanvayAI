"""Canonical Unit of Measure (UoM) Engine.

Conforms to specsheet.md Section 7.6:
- Controlled vocabulary: EA, SET, M, KM, KG, MT, LTR, PAIR, ROLL, DRUM, LOT, 100EA, FT.
- Canonical base:
  - sections and rebar in MT
  - cables and pipes in M
  - equipment in EA
- Physical conversion formulas:
  - rebar: kg/m = (d^2)/162 (d in mm)
  - structural sections: from section_properties.csv (IS 808)
  - plates: thickness_mm * width_m * length_m * 7.85 kg
  - pipes: (OD - WT) * WT * 0.02466 kg/m (OD and WT in mm)
- Safety Invariant:
  A conversion requiring an unknown attribute raises MissingConversionAttribute
  (recorded as a flag), NEVER guesses.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

DICTIONARIES_DIR = Path(__file__).resolve().parent.parent.parent / "dictionaries"
# VERIFY: VERIFY-004 (IS 808 structural steel profile kg/m properties)
SECTION_PROPERTIES_FILE = DICTIONARIES_DIR / "section_properties.csv"

# Controlled Vocabulary (specsheet Section 7.6)
CONTROLLED_UOM = {
    "EA",
    "SET",
    "M",
    "KM",
    "KG",
    "MT",
    "LTR",
    "PAIR",
    "ROLL",
    "DRUM",
    "LOT",
    "100EA",
    "FT",
}

# Alias Map to Controlled Vocabulary
UOM_ALIASES: dict[str, str] = {
    # Count / Pieces
    "EA": "EA",
    "NOS": "EA",
    "NO": "EA",
    "NUM": "EA",
    "NUMBER": "EA",
    "PIECE": "EA",
    "PIECES": "EA",
    "PCS": "EA",
    "PC": "EA",
    "EACH": "EA",
    "UNIT": "EA",
    "UNITS": "EA",
    # Hundred Count
    "100EA": "100EA",
    "CENT": "100EA",
    "C": "100EA",
    "HUNDRED": "100EA",
    # Sets / Pairs
    "SET": "SET",
    "SETS": "SET",
    "PAIR": "PAIR",
    "PAIRS": "PAIR",
    "PR": "PAIR",
    # Length
    "M": "M",
    "MTR": "M",
    "MTRS": "M",
    "METER": "M",
    "METRE": "M",
    "METERS": "M",
    "METRES": "M",
    "KM": "KM",
    "KMS": "KM",
    "KILOMETER": "KM",
    "KILOMETRE": "KM",
    "FT": "FT",
    "FEET": "FT",
    "FOOT": "FT",
    # Mass
    "KG": "KG",
    "KGS": "KG",
    "KILOGRAM": "KG",
    "KILOGRAMS": "KG",
    "MT": "MT",
    "TON": "MT",
    "TONS": "MT",
    "TONNE": "MT",
    "TONNES": "MT",
    "METRIC TON": "MT",
    # Volume
    "LTR": "LTR",
    "L": "LTR",
    "LITER": "LTR",
    "LITRE": "LTR",
    "LITERS": "LTR",
    "LITRES": "LTR",
    # Packaging / Lots
    "ROLL": "ROLL",
    "ROLLS": "ROLL",
    "DRUM": "DRUM",
    "DRUMS": "DRUM",
    "LOT": "LOT",
    "LOTS": "LOT",
}

# Default canonical target per category
CATEGORY_CANONICAL_TARGET: dict[str, str] = {
    "SECTIONS": "MT",
    "REBAR": "MT",
    "STEEL": "MT",
    "PLATES": "MT",
    "CABLES": "M",
    "PIPES": "M",
    "VALVES": "EA",
    "PUMPS": "EA",
    "MOTORS": "EA",
    "TRANSFORMERS": "EA",
    "BEARINGS": "EA",
    "FASTENERS": "EA",  # Or SET if defined
    # Extended dotted subcategories across domain packs (Section 18.9)
    "STEEL.CONVEYOR_BELT": "M",
    "MINING.WIRE_ROPE": "M",
    "HEAVY.HYDRAULIC_HOSE": "M",
    "POWER.BOILER_TUBE": "M",
    "STEEL.REFRACTORY": "MT",
    "MINING.OTR_TYRE": "EA",
    "POWER.TRANSFORMER": "EA",
    "POWER.BREAKER": "EA",
    "HEAVY.PUMP_CENTRIFUGAL": "EA",
    "HEAVY.MADE_TO_DRAWING": "EA",
    "STEEL.MILL_ROLL": "EA",
}

# Dimension canonical base for dimension scalar reductions
DIMENSION_CANONICAL_BASE: dict[str, str] = {
    "KM": "M",
    "FT": "M",
    "M": "M",
    "KG": "MT",
    "MT": "MT",
    "100EA": "EA",
    "EA": "EA",
    "LTR": "LTR",
    "SET": "SET",
    "PAIR": "PAIR",
    "ROLL": "ROLL",
    "DRUM": "DRUM",
    "LOT": "LOT",
}


class MissingConversionAttribute(Exception):
    """Raised when a physical conversion requires attributes that are not provided."""

    def __init__(self, message: str, required_attribute: str | None = None) -> None:
        super().__init__(message)
        self.required_attribute = required_attribute


@dataclass
class CanonicalUoMResult:
    """Result of UoM standardization and canonical conversion."""

    original_qty: float
    original_uom: str
    standard_uom: str
    canonical_qty: float
    canonical_uom: str
    conversion_factor: float = 1.0
    flags: list[str] = field(default_factory=list)
    conversion_note: str | None = None


class SectionPropertiesRegistry:
    """Lookup table for IS 808 structural steel sections."""

    def __init__(self) -> None:
        self.properties: dict[str, float] = {}
        self._load()

    def _normalize_key(self, designation: str) -> str:
        return designation.strip().upper().replace(" ", "").replace("-", "")

    def _load(self) -> None:
        if not SECTION_PROPERTIES_FILE.exists():
            return
        with open(SECTION_PROPERTIES_FILE, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                desig = row.get("designation", "").strip()
                kg_m_str = row.get("kg_per_m", "").strip()
                if desig and kg_m_str:
                    try:
                        kg_m = float(kg_m_str)
                        self.properties[self._normalize_key(desig)] = kg_m
                    except ValueError:
                        continue

    def get_kg_per_m(self, designation: str) -> float | None:
        key = self._normalize_key(designation)
        if key in self.properties:
            return self.properties[key]
        # Search if any profile designation is present in the designation string (longest first)
        for prop_key, val in sorted(self.properties.items(), key=lambda kv: len(kv[0]), reverse=True):
            if prop_key in key:
                return val
        return None


_SECTION_REGISTRY: SectionPropertiesRegistry | None = None


def get_section_registry() -> SectionPropertiesRegistry:
    global _SECTION_REGISTRY
    if _SECTION_REGISTRY is None:
        _SECTION_REGISTRY = SectionPropertiesRegistry()
    return _SECTION_REGISTRY


def standardize_uom(raw_uom: str) -> tuple[str, list[str]]:
    """Map raw UoM string to controlled vocabulary.

    Returns:
        (standard_uom, flags)
    """
    clean = raw_uom.strip().upper().rstrip(".")
    if clean in CONTROLLED_UOM:
        return clean, []
    if clean in UOM_ALIASES:
        return UOM_ALIASES[clean], []
    # If not recognized, return raw uppercase and flag
    return clean, ["UNKNOWN_UOM"]


def convert_to_canonical(
    qty: float,
    raw_uom: str,
    category: str | None = None,
    attributes: dict | None = None,
) -> CanonicalUoMResult:
    """Convert quantity and UoM to canonical base unit.

    Args:
        qty: Input quantity.
        raw_uom: Input unit of measure string.
        category: Material family/category.
        attributes: Extracted or row attributes for physical conversion.

    Returns:
        CanonicalUoMResult with canonical quantity, unit, factor, and flags.
    """
    attrs = attributes or {}
    cat_upper = category.upper() if category else None
    std_uom, uom_flags = standardize_uom(raw_uom)
    flags = list(uom_flags)

    # Base target unit
    if cat_upper and cat_upper in CATEGORY_CANONICAL_TARGET:
        target_uom = CATEGORY_CANONICAL_TARGET[cat_upper]
    elif cat_upper and "." in cat_upper:
        prefix, suffix = cat_upper.split(".", 1)
        target_uom = (
            CATEGORY_CANONICAL_TARGET.get(cat_upper)
            or CATEGORY_CANONICAL_TARGET.get(suffix)
            or CATEGORY_CANONICAL_TARGET.get(prefix)
            or DIMENSION_CANONICAL_BASE.get(std_uom, std_uom)
        )
    else:
        target_uom = DIMENSION_CANONICAL_BASE.get(std_uom, std_uom)

    # 1. Identity / Same unit
    if std_uom == target_uom:
        return CanonicalUoMResult(
            original_qty=qty,
            original_uom=raw_uom,
            standard_uom=std_uom,
            canonical_qty=qty,
            canonical_uom=std_uom,
            conversion_factor=1.0,
            flags=flags,
            conversion_note="Direct match",
        )

    # 2. Simple scalar conversions within same dimension
    # 100EA -> EA
    if std_uom == "100EA" and target_uom == "EA":
        return CanonicalUoMResult(
            original_qty=qty,
            original_uom=raw_uom,
            standard_uom=std_uom,
            canonical_qty=qty * 100.0,
            canonical_uom="EA",
            conversion_factor=100.0,
            flags=flags,
            conversion_note="100EA to EA (* 100)",
        )

    # KM -> M
    if std_uom == "KM" and target_uom == "M":
        return CanonicalUoMResult(
            original_qty=qty,
            original_uom=raw_uom,
            standard_uom=std_uom,
            canonical_qty=qty * 1000.0,
            canonical_uom="M",
            conversion_factor=1000.0,
            flags=flags,
            conversion_note="KM to M (* 1000)",
        )

    # FT -> M
    if std_uom == "FT" and target_uom == "M":
        return CanonicalUoMResult(
            original_qty=qty,
            original_uom=raw_uom,
            standard_uom=std_uom,
            canonical_qty=qty * 0.3048,
            canonical_uom="M",
            conversion_factor=0.3048,
            flags=flags,
            conversion_note="FT to M (* 0.3048)",
        )

    # KG -> MT
    if std_uom == "KG" and target_uom == "MT":
        return CanonicalUoMResult(
            original_qty=qty,
            original_uom=raw_uom,
            standard_uom=std_uom,
            canonical_qty=qty / 1000.0,
            canonical_uom="MT",
            conversion_factor=0.001,
            flags=flags,
            conversion_note="KG to MT (/ 1000)",
        )

    # MT -> KG
    if std_uom == "MT" and target_uom == "KG":
        return CanonicalUoMResult(
            original_qty=qty,
            original_uom=raw_uom,
            standard_uom=std_uom,
            canonical_qty=qty * 1000.0,
            canonical_uom="KG",
            conversion_factor=1000.0,
            flags=flags,
            conversion_note="MT to KG (* 1000)",
        )

    # 3. Packaging conversions with length
    if std_uom in ("ROLL", "DRUM") and target_uom == "M":
        length_per_pack = attrs.get("length_m") or attrs.get("pack_length_m")
        if length_per_pack is not None:
            try:
                l_val = float(length_per_pack)
                return CanonicalUoMResult(
                    original_qty=qty,
                    original_uom=raw_uom,
                    standard_uom=std_uom,
                    canonical_qty=qty * l_val,
                    canonical_uom="M",
                    conversion_factor=l_val,
                    flags=flags,
                    conversion_note=f"{std_uom} to M with {l_val}m per pack",
                )
            except ValueError:
                pass
        flags.append("MISSING_CONVERSION_ATTRIBUTE")
        return CanonicalUoMResult(
            original_qty=qty,
            original_uom=raw_uom,
            standard_uom=std_uom,
            canonical_qty=qty,
            canonical_uom=std_uom,
            flags=flags,
            conversion_note=f"Missing pack length to convert {std_uom} to M",
        )

    # 4. Fasteners SET definition
    if cat_upper == "FASTENERS" and std_uom == "SET":
        set_def = attrs.get("set_definition")
        if not set_def:
            flags.append("MISSING_CONVERSION_ATTRIBUTE")
            return CanonicalUoMResult(
                original_qty=qty,
                original_uom=raw_uom,
                standard_uom=std_uom,
                canonical_qty=qty,
                canonical_uom="SET",
                flags=flags,
                conversion_note="Fastener SET requires set_definition",
            )

    # 5. Physical dimensional conversions (Section 7.6)
    try:
        # Rebar (length in M -> MT)
        if cat_upper == "REBAR" and std_uom == "M" and target_uom == "MT":
            d = attrs.get("diameter_mm") or attrs.get("rebar_diameter") or attrs.get("size_mm")
            if d is None:
                raise MissingConversionAttribute(
                    "Rebar conversion M -> MT requires diameter_mm (kg/m = d^2/162)",
                    required_attribute="diameter_mm",
                )
            d_val = float(d)
            kg_per_m = (d_val**2) / 162.0
            total_kg = qty * kg_per_m
            canonical_mt = total_kg / 1000.0
            factor = kg_per_m / 1000.0
            return CanonicalUoMResult(
                original_qty=qty,
                original_uom=raw_uom,
                standard_uom=std_uom,
                canonical_qty=canonical_mt,
                canonical_uom="MT",
                conversion_factor=factor,
                flags=flags,
                conversion_note=f"Rebar d={d_val}mm formula kg/m=d^2/162",
            )

        # Structural sections (length in M -> MT via IS 808 lookup)
        if cat_upper in ("SECTIONS", "STEEL") and std_uom == "M" and target_uom == "MT":
            desig = attrs.get("designation") or attrs.get("profile") or attrs.get("section")
            if not desig:
                raise MissingConversionAttribute(
                    "Section conversion M -> MT requires designation for IS 808 lookup",
                    required_attribute="designation",
                )
            registry = get_section_registry()
            kg_per_m = registry.get_kg_per_m(str(desig))
            if kg_per_m is None:
                raise MissingConversionAttribute(
                    f"Section designation '{desig}' not found in IS 808 reference table",
                    required_attribute="designation",
                )
            total_kg = qty * kg_per_m
            canonical_mt = total_kg / 1000.0
            factor = kg_per_m / 1000.0
            return CanonicalUoMResult(
                original_qty=qty,
                original_uom=raw_uom,
                standard_uom=std_uom,
                canonical_qty=canonical_mt,
                canonical_uom="MT",
                conversion_factor=factor,
                flags=flags,
                conversion_note=f"IS 808 section '{desig}' at {kg_per_m} kg/m",
            )

        # Steel plates (count in EA -> MT via t * w * l * 7.85)
        if cat_upper == "PLATES" and std_uom in ("EA", "NOS") and target_uom == "MT":
            thk = attrs.get("thickness_mm")
            w = attrs.get("width_m")
            l = attrs.get("length_m")
            if thk is None or w is None or l is None:
                raise MissingConversionAttribute(
                    "Plate conversion EA -> MT requires thickness_mm, width_m, length_m",
                    required_attribute="plate_dimensions",
                )
            thk_val = float(thk)
            w_val = float(w)
            l_val = float(l)
            kg_per_plate = thk_val * w_val * l_val * 7.85
            canonical_mt = (qty * kg_per_plate) / 1000.0
            factor = kg_per_plate / 1000.0
            return CanonicalUoMResult(
                original_qty=qty,
                original_uom=raw_uom,
                standard_uom=std_uom,
                canonical_qty=canonical_mt,
                canonical_uom="MT",
                conversion_factor=factor,
                flags=flags,
                conversion_note=f"Plate {thk_val}mm x {w_val}m x {l_val}m @ 7.85 kg/mm-m2",
            )

        # Pipes (weight in MT or KG -> canonical M)
        if cat_upper == "PIPES" and std_uom in ("MT", "KG") and target_uom == "M":
            od = attrs.get("od_mm")
            wt = attrs.get("wt_mm") or attrs.get("wall_thickness_mm")
            if od is None or wt is None:
                raise MissingConversionAttribute(
                    "Pipe weight to length conversion requires od_mm and wt_mm",
                    required_attribute="pipe_dimensions",
                )
            od_val = float(od)
            wt_val = float(wt)
            kg_per_m = (od_val - wt_val) * wt_val * 0.02466
            if kg_per_m <= 0:
                raise MissingConversionAttribute(
                    f"Physically invalid pipe dimensions OD={od_val}, WT={wt_val}",
                    required_attribute="pipe_dimensions",
                )
            weight_kg = qty * 1000.0 if std_uom == "MT" else qty
            canonical_m = weight_kg / kg_per_m
            factor = 1.0 / kg_per_m if std_uom == "KG" else 1000.0 / kg_per_m
            return CanonicalUoMResult(
                original_qty=qty,
                original_uom=raw_uom,
                standard_uom=std_uom,
                canonical_qty=canonical_m,
                canonical_uom="M",
                conversion_factor=factor,
                flags=flags,
                conversion_note=f"Pipe OD={od_val}mm WT={wt_val}mm at {kg_per_m:.3f} kg/m",
            )

    except (MissingConversionAttribute, ValueError, TypeError) as err:
        flags.append("MISSING_CONVERSION_ATTRIBUTE")
        return CanonicalUoMResult(
            original_qty=qty,
            original_uom=raw_uom,
            standard_uom=std_uom,
            canonical_qty=qty,
            canonical_uom=std_uom,
            flags=flags,
            conversion_note=str(err),
        )

    # Default fallback: keep standard UoM if no cross-unit conversion path exists
    return CanonicalUoMResult(
        original_qty=qty,
        original_uom=raw_uom,
        standard_uom=std_uom,
        canonical_qty=qty,
        canonical_uom=std_uom,
        conversion_factor=1.0,
        flags=flags,
        conversion_note="Standardized UoM",
    )
