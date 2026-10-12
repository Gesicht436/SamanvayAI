"""Safety tests for NER Token Classification and Invariant S12 cross-validation.

Non-negotiable invariants tested:
- S12: NER is NEVER the sole source of a HARD or statutory attribute.
- Cross-validation: Disagreement between NER and deterministic extractors lowers confidence
  and raises flag 'NER_DETERMINISTIC_DISAGREEMENT', and deterministic extractor is NEVER overridden.
- When NER is the sole source, confidence is strictly capped (<= 0.40) with
  'NER_UNVALIDATED_BY_DETERMINISTIC_RULES' so it cannot auto-harmonize in Tier 1.
- Reconciliation: Donor B's 6 labels reconcile cleanly into A's 12 token classes.
- Metrics Honesty: Per-label Precision, Recall, and F1 are computed from observed counts only.
"""

from __future__ import annotations

import json
from pathlib import Path

from api.extractors.base import ExtractedValue
from api.ml.ner import (
    B_TO_A_LABEL_MAPPING,
    TOKEN_CLASSES,
    cross_check_ner_with_deterministic_extractors,
    get_ner_extractor,
)
from scripts.train_ner import (
    compute_per_label_metrics,
    map_b_label_to_canonical,
    train_ner,
)


def test_b_to_a_label_reconciliation_mapping() -> None:
    """Verifies that B's 6 label types map accurately to A's 12 canonical token classes."""
    assert map_b_label_to_canonical("ITEM_TYPE") == "ITEM_TYPE"
    assert map_b_label_to_canonical("SIZE") == "SIZE"
    assert map_b_label_to_canonical("PRESSURE_RATING") == "PRESSURE"
    assert map_b_label_to_canonical("METALLURGY") == "METALLURGY"
    assert map_b_label_to_canonical("STANDARD") == "STANDARD"

    # Disambiguation of FACING_END
    assert map_b_label_to_canonical("FACING_END", "RAISED FACE") == "FACING"
    assert map_b_label_to_canonical("FACING_END", "RTJ") == "FACING"
    assert map_b_label_to_canonical("FACING_END", "BUTTWELD (BW)") == "END_CONN"
    assert map_b_label_to_canonical("FACING_END", "SOCKET WELD") == "END_CONN"

    # All targets must exist in A's TOKEN_CLASSES
    for b_label, a_class in B_TO_A_LABEL_MAPPING.items():
        assert a_class in TOKEN_CLASSES, f"Target {a_class} for {b_label} must be in TOKEN_CLASSES"


def test_invariant_s12_ner_disagreement_lowers_confidence_never_overrides() -> None:
    """Invariant S12: When NER disagrees with deterministic extractors on a HARD attribute,

    deterministic extractor remains authoritative; confidence is penalized and flag is raised.
    """
    deterministic = {
        "pressure_class": ExtractedValue(value="150", confidence=0.95, source="regex"),
        "size_nb": ExtractedValue(value="100", confidence=0.95, source="regex"),
        "body_material": ExtractedValue(value="WCB", confidence=0.95, source="regex"),
    }
    # NER predicts conflicting pressure class 300
    ner_attrs = {
        "pressure_class": ExtractedValue(value="300", confidence=0.90, source="ner"),
        "size_nb": ExtractedValue(value="100", confidence=0.90, source="ner"),  # Agree
        "body_material": ExtractedValue(value="WCB", confidence=0.90, source="ner"),  # Agree
    }

    harmonized, flags = cross_check_ner_with_deterministic_extractors(ner_attrs, deterministic)

    # Invariant S12 Assertions:
    # 1. Deterministic value NEVER overridden
    assert harmonized["pressure_class"].value == "150"
    assert harmonized["pressure_class"].value != "300"

    # 2. Confidence is penalized due to disagreement
    assert harmonized["pressure_class"].confidence <= 0.50

    # 3. Discrepancy flag raised
    assert "NER_DETERMINISTIC_DISAGREEMENT" in harmonized["pressure_class"].flags
    assert any("NER_DETERMINISTIC_DISAGREEMENT" in f for f in flags)

    # 4. Agreed attributes retain high confidence
    assert harmonized["size_nb"].value == "100"
    assert harmonized["size_nb"].confidence >= 0.95


def test_invariant_s12_ner_sole_source_cannot_auto_harmonize() -> None:
    """Invariant S12: When an attribute is found ONLY by NER, confidence is capped low

    and flagged with 'NER_UNVALIDATED_BY_DETERMINISTIC_RULES' so it cannot auto-harmonize.
    """
    deterministic = {
        "size_nb": ExtractedValue(value="50", confidence=0.95, source="regex"),
    }
    # NER proposes pressure_class and material_grade that deterministic extractor didn't find
    ner_attrs = {
        "pressure_class": ExtractedValue(value="600", confidence=0.88, source="ner"),
        "material_grade": ExtractedValue(value="A105", confidence=0.88, source="ner"),
    }

    harmonized, flags = cross_check_ner_with_deterministic_extractors(ner_attrs, deterministic)

    # Invariant S12 Assertions:
    assert harmonized["pressure_class"].confidence <= 0.40
    assert "NER_UNVALIDATED_BY_DETERMINISTIC_RULES" in harmonized["pressure_class"].flags

    assert harmonized["material_grade"].confidence <= 0.40
    assert "NER_UNVALIDATED_BY_DETERMINISTIC_RULES" in harmonized["material_grade"].flags

    assert any("NER_UNVALIDATED_BY_DETERMINISTIC_RULES" in f for f in flags)


def test_learned_ner_fallback_without_weights() -> None:
    """Verifies that LearnedNERExtractor falls back to regex tagger with visible flags

    when trained weights directory does not exist.
    """
    extractor, flags = get_ner_extractor(prefer_learned=True, weights_dir="non_existent_model_dir")

    assert "ML_MODEL_UNAVAILABLE" in flags
    assert "REGEX_NER_FALLBACK" in flags

    attrs = extractor.extract_attributes("VALVE GATE 100 NB CL150 WCB RF")
    assert len(attrs) > 0
    # Every extracted value carries the fallback flag
    for v in attrs.values():
        assert "REGEX_NER_FALLBACK" in v.flags


def test_per_label_metrics_calculation_in_train_ner() -> None:
    """Verifies compute_per_label_metrics calculates honest Precision, Recall, and F1 from counts."""
    true_seqs = [
        ["B-ITEM_TYPE", "O", "B-SIZE", "B-PRESSURE"],
        ["B-METALLURGY", "O", "B-STANDARD"],
    ]
    pred_seqs = [
        ["B-ITEM_TYPE", "O", "B-SIZE", "O"],  # Missed PRESSURE (FN for PRESSURE)
        ["B-METALLURGY", "O", "B-STANDARD"],  # Exact match
    ]

    metrics = compute_per_label_metrics(
        true_seqs,
        pred_seqs,
        labels=["ITEM_TYPE", "SIZE", "PRESSURE", "METALLURGY", "STANDARD"],
    )

    assert metrics["ITEM_TYPE"]["precision"] == 1.0
    assert metrics["ITEM_TYPE"]["recall"] == 1.0
    assert metrics["ITEM_TYPE"]["f1"] == 1.0

    assert metrics["PRESSURE"]["precision"] == 0.0
    assert metrics["PRESSURE"]["recall"] == 0.0
    assert metrics["PRESSURE"]["f1"] == 0.0

    assert metrics["macro_f1"] > 0.0


def test_train_ner_smoke_run(tmp_path: Path) -> None:
    """Verifies train_ner smoke run completes without error."""
    sample_file = tmp_path / "ner_smoke.jsonl"
    rows = [
        {
            "text": "FLANGE WNRF 4 IN 150# A105",
            "labels": [
                {"start": 0, "end": 11, "label": "ITEM_TYPE"},
                {"start": 12, "end": 16, "label": "SIZE"},
                {"start": 17, "end": 21, "label": "PRESSURE_RATING"},
                {"start": 22, "end": 26, "label": "METALLURGY"},
            ],
        }
    ]
    with open(sample_file, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)

    out_dir = tmp_path / "ner_smoke_out"
    metrics = train_ner(train_file=sample_file, output_dir=out_dir, smoke_run=True)

    assert isinstance(metrics, dict)
    assert "macro_f1" in metrics
