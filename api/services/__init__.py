"""Samanvay Core Services: Normalization, Extraction, Retrieval, Comparator, Tiering, Lifecycle, and Dedup."""

from api.services.candidates import (
    RetrievedCandidate,
    compute_block_key,
    retrieve_candidates_db,
    retrieve_candidates_in_memory,
)
from api.services.classify import (
    ClassificationResult,
    classify_subcategory,
)
from api.services.cold_start import (
    ClusteredMaster,
    ColdStartEngine,
    DedupReport,
    RawItemRecord,
)
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
from api.services.lifecycle import (
    create_golden_master,
    generate_canonical_text,
    generate_descriptor,
    merge_golden_masters,
    split_golden_master,
    update_master_status,
)
from api.services.normalize import NormalizationResult, normalize_text
from api.services.scoring import (
    MatchFeatures,
    ScoringResult,
    extract_match_features,
    score_candidate,
)
from api.services.script_detector import ScriptDetectionResult, detect_scripts
from api.services.stewardship import (
    approve_steward_task,
    create_steward_task,
    get_steward_task,
    list_steward_tasks,
    reject_steward_task,
)
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
    "ClassificationResult",
    "ClusteredMaster",
    "ColdStartEngine",
    "DedupReport",
    "IngestedRow",
    "IngestionResult",
    "ItemComparisonResult",
    "MatchFeatures",
    "MissingConversionAttribute",
    "NormalizationResult",
    "ParsedTabularData",
    "RawItemRecord",
    "RetrievedCandidate",
    "ScoringResult",
    "ScriptDetectionResult",
    "Tier",
    "TieringResult",
    "Verdict",
    "approve_steward_task",
    "assign_tier",
    "classify_subcategory",
    "compare_items",
    "compute_block_key",
    "convert_to_canonical",
    "create_golden_master",
    "create_steward_task",
    "detect_scripts",
    "evaluate_attribute_verdict",
    "extract_match_features",
    "generate_canonical_text",
    "generate_descriptor",
    "get_steward_task",
    "ingest_tabular_document",
    "list_steward_tasks",
    "merge_golden_masters",
    "normalize_text",
    "parse_tabular_bytes",
    "reject_steward_task",
    "retrieve_candidates_db",
    "retrieve_candidates_in_memory",
    "score_candidate",
    "split_golden_master",
    "standardize_uom",
    "update_master_status",
]
