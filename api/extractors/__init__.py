"""Extractor Framework and Spec Registry package."""

from api.extractors.base import BaseExtractor, ExtractedValue, none_with
from api.extractors.lexicon import LexiconExtractor, load_lexicon_data
from api.extractors.parsers.pressure_class import extract_pressure_class
from api.extractors.parsers.size_nb import extract_size_nb
from api.extractors.registry import (
    AttributeRole,
    AttributeSpecDef,
    IdentityMode,
    SpecRegistry,
    SubcategorySpecDef,
    default_registry,
)

__all__ = [
    "AttributeRole",
    "AttributeSpecDef",
    "BaseExtractor",
    "ExtractedValue",
    "IdentityMode",
    "LexiconExtractor",
    "SpecRegistry",
    "SubcategorySpecDef",
    "default_registry",
    "extract_pressure_class",
    "extract_size_nb",
    "load_lexicon_data",
    "none_with",
]
