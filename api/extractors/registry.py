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
from api.extractors.parsers.pressure_class import extract_pressure_class
from api.extractors.parsers.size_nb import extract_size_nb
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
    value: int | float
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
        """Registers core Python parsers for physical attributes."""
        self.register_parser("size_nb", extract_size_nb)
        self.register_parser("pressure_class", extract_pressure_class)

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

            # Check dedicated Python parser
            if name in self._python_parsers:
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
