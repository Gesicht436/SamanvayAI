"""Samanvay Core Services: Script Detector, Text Normalization, UoM Engine, and Ingest."""

from api.services.ingest import (
    IngestedRow,
    IngestionResult,
    ParsedTabularData,
    ingest_tabular_document,
    parse_tabular_bytes,
)
from api.services.normalize import NormalizationResult, normalize_text
from api.services.script_detector import ScriptDetectionResult, detect_scripts
from api.services.uom import (
    CanonicalUoMResult,
    MissingConversionAttribute,
    convert_to_canonical,
    standardize_uom,
)

__all__ = [
    "CanonicalUoMResult",
    "IngestedRow",
    "IngestionResult",
    "MissingConversionAttribute",
    "NormalizationResult",
    "ParsedTabularData",
    "ScriptDetectionResult",
    "convert_to_canonical",
    "detect_scripts",
    "ingest_tabular_document",
    "normalize_text",
    "parse_tabular_bytes",
    "standardize_uom",
]
