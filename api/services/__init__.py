"""Samanvay Core Services: Script Detector, Text Normalization, UoM Engine, Ingest, Comparator, and Tiering."""

from api.services.comparator import (
    AttributeVerdictResult,
    ItemComparisonResult,
    Verdict,
    compare_items,
    evaluate_attribute_verdict,
)
from api.services.ingest import (
    IngestedRow,
    IngestionResult,
    ParsedTabularData,
    ingest_tabular_document,
    parse_tabular_bytes,
)
from api.services.normalize import NormalizationResult, normalize_text
from api.services.script_detector import ScriptDetectionResult, detect_scripts
from api.services.tiering import Tier, TieringResult, assign_tier
from api.services.uom import (
    CanonicalUoMResult,
    MissingConversionAttribute,
    convert_to_canonical,
    standardize_uom,
)

__all__ = [
    "AttributeVerdictResult",
    "CanonicalUoMResult",
    "IngestedRow",
    "IngestionResult",
    "ItemComparisonResult",
    "MissingConversionAttribute",
    "NormalizationResult",
    "ParsedTabularData",
    "ScriptDetectionResult",
    "Tier",
    "TieringResult",
    "Verdict",
    "assign_tier",
    "compare_items",
    "convert_to_canonical",
    "detect_scripts",
    "evaluate_attribute_verdict",
    "ingest_tabular_document",
    "normalize_text",
    "parse_tabular_bytes",
    "standardize_uom",
]
