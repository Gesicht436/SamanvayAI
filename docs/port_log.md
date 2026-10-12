# Port Log: Donor Repo B to Repo A

This document logs all ported features, modifications, tests, metrics, and dependencies phase by phase.

---

## Phase 0: Baseline & Setup

- **Branch Created**: `port-b-features`
- **Confirmation of Donor Repo B Access**: Verified `./Samanvay.AI/OCR/engine.py` exists and is readable.
- **Ruff Configuration**: Added `"Samanvay.AI"` to `exclude` in `pyproject.toml`. Added optional dependencies extra `[project.optional-dependencies] ml`.
- **Baseline Test Suite**:
  - Command: `uv run pytest`
  - Results: 234 passed, 0 failed, 0 skipped, 1 deprecation warning (`starlette.testclient`).
- **Baseline Evaluation Harness**:
  - Command: `uv run python scripts/eval_harness.py`
  - Backup: `metrics.baseline.json` created from `metrics.json`.
  - Results:
    - Adversarial Hard Negatives (170 pairs): 0 false merges (0.0%, 95% Clopper-Pearson interval [0.00%, 2.15%]).
    - Missing attribute routing (S1): 76/76 routed to Tier 2 (100.0%, 95% interval [95.26%, 100.00%]).
    - Low-confidence OCR in Tier 1: 0 found.
    - MTC conforms against unverified reference: 0 found.
    - Auto-tier precision (dev): 100.00% (600/600, note: pre-existing weakness in A where fixtures rows were merely counted rather than executed through extraction/matching pipeline).
    - Status: ALL GATES PASSED.
- **Pre-existing Failures**: None.
- **Dependencies & Environment**: Python 3.12.15 on Windows. Dependencies managed via `uv`. Heavy ML dependencies kept in optional extra `ml`.

---

## Phase 1: Real OCR

- **What was ported**:
  - `PaddleOCREngine` and `EasyOCREngine` adapted from B (`OCR/engine.py`), handling 2.x and 3.x result shapes and score thresholds.
  - `_reading_order` grouping bounding boxes with overlapping vertical projections into lines and sorting left-to-right, then ordering lines top-to-bottom by median y.
  - `PaddleOCRProvider`, `EasyOCRProvider`, and `HybridOCRProvider` added to `api/services/ocr.py`.
  - Full-page fast image preprocessing `preprocess_scanned_image` with 3x3 median filtering, row projection deskew estimation, and autocontrast via Pillow/numpy, with graceful non-Pillow fallback.
  - Real per-block OCR confidence scores from engines aggregated to line `ocr_conf` and page `mean_confidence`.
  - Normalized bbox coordinates `[x0, y0, x1, y1]` in [0.0, 1.0].
  - Cleaned up `LocalNeuralOCRProvider` to parse tesseract TSV word confidences instead of fixed 0.94 constant.
- **What was changed from B**:
  - Replaced B's standalone return dicts with A's `OCRProvider` protocol types (`OCRDocumentResult`, `OCRPageResult`, `OCRLine`).
  - Removed misleading aliases where "easyocr" and "paddleocr" mapped to `LocalNeuralOCRProvider` (tesseract). Provider names now strictly instantiate what they claim (`get_ocr_provider`).
  - Replaced hard-coded 0.82 confidence on PyMuPDF scanned pages with real 0.0 unread scan confidence with explicit `NO_DIGITAL_TEXT_LAYER` and `LOW_OCR_CONFIDENCE` flags.
  - In `api/services/comparator.py`, unwrapped attribute value dictionaries and ExtractedValue objects in `evaluate_attribute_verdict` so sanitized `LOW_OCR_CONFIDENCE` dictionaries correctly evaluate to `Verdict.MISSING` rather than scalar mismatches.
- **Tests Added**:
  - `test_ocr_provider_factory_distinct_providers`: verifies provider factory maps each name to its true class without aliasing tesseract.
  - `test_paddleocr_provider_mock_replay_and_reading_order`: verifies mocked PaddleOCR engine output replay, reading-order sorting, and confidence propagation.
  - `test_easyocr_provider_mock_replay`: verifies EasyOCR output replay and normalized bounding box mapping.
  - `test_hybrid_ocr_per_page_fallback`: verifies per-page fallback from PaddleOCR to EasyOCR.
  - `test_ocr_graceful_fallback_without_ml_extra`: verifies graceful degradation with visible flags (`ML_MODEL_UNAVAILABLE`, `OCR_PROVIDER_UNAVAILABLE`, `LOW_OCR_CONFIDENCE`).
  - `test_invariant_s5_real_ocr_confidence_gates_to_tier2`: verifies low real OCR confidence on HARD attributes blanks values and gates strictly to Tier 2.
  - Total test count: 240 passed (up from 234 baseline).
- **Eval-Harness Before / After**:
  - Baseline: 0/170 false merges ([0.00%, 2.15%]), 76/76 missing attribute routed to Tier 2 (100.0%).
  - Phase 1: 0/170 false merges ([0.00%, 2.15%]), 76/76 missing attribute routed to Tier 2 (100.0%).
- **Dependencies Pinned**:
  - `paddleocr>=2.8.0`, `easyocr>=1.7.1`, `pillow>=10.4.0` in optional extra `ml`.

---

## Phase 2: MTC Extraction Fixes

- **What was ported**:
  - Table parsing logic for MTC certificates: vertical one-cell-per-line tables (K header lines followed by K value lines) and horizontal row tables.
  - Header cleaning supporting % and unit annotations: `"C%"`, `"Mn%"`, `"Si%"`, `"P%"`, `"S%"`, `"Yield (MPa)"`, `"Tensile (MPa)"`, `"Elongation (%)"`, `"Hardness (HBW)"`, `"Hardness (HRC)"`, `"Hydro Shell (bar)"`, `"Hydro Seat (bar)"`, `"Air Seat (bar)"`, `"Visual Inspection"`.
  - Decimal-comma normalization: `re.sub(r"(?<=\d),(?=\d)", ".", text)` before table and key-value extraction so values like `"0,21 1,15"` are never corrupted by splitting on the comma into `C=0, Mn=21`.
  - Whole-token chemistry context matching: token boundary isolation preventing `"ASME B16.5"` or `"B16."` from being misread as Boron (`B=16.5`).
  - Donor test fixtures: copied 4 MTC PDFs (`sample_mtc_flange_01.pdf`, `sample_mtc_valve_02.pdf`, `sample_mtc_flange_ss_03.pdf`, `sample_mtc_bolt_04.pdf`), 1 inspection challan (`sample_challan_valve_05.pdf`), and `sample_mtc_ground_truth.json` into `tests/fixtures/mtc/`.
  - Metallurgical Grade Specifications: added grade-aware limits distinguishing `ASTM A182 F316L` (C max 0.030%, ASTM A182 Table 2, UNS S31603) from `ASTM A182 F316` (C max 0.080%, UNS S31600).
- **What was changed from B**:
  - Rejected B's dangerous shortcut of treating missing elements as zero in CE/PREN. A's strict invariants preserved: `CE_INCOMPLETE` and `PREN_INCOMPLETE` raised if any required constituent is absent.
  - Rejected B's shortcut that used F316 limits for F316L.
  - Maintained Invariant S15: MTC evaluation against unverified reference rows returns `UNVERIFIED_REFERENCE` and requires human review.
  - Kept bounds validation: chemistry values <0 or >100 flagged with `CHEM_OUT_OF_RANGE_*`, sum > 100 flagged with `CHEM_SUM_EXCEEDS_100`.
- **Tests Added**:
  - `test_mtc_sample_pdf_fixtures_extraction_both_modes`: PyMuPDF plain text and layout/sorted-block extraction on all 5 sample PDFs against ground truth chemistry and mechanical properties.
  - `test_mtc_decimal_comma_table_without_splitting`: regression test that `"0,21 1,15"` parses as C=0.21, Mn=1.15.
  - `test_mtc_b16_5_is_not_misread_as_boron`: regression test that `ASME B16.5` does not extract Boron.
  - `test_mtc_grade_limits_f316_vs_f316l_carbon_distinction`: verifies C max 0.030% for F316L vs 0.080% for F316.
  - Total test count: 244 passed (up from 240 in Phase 1, 234 baseline).
- **Eval-Harness Before / After**:
  - Baseline & Phase 1: 0/170 false merges ([0.00%, 2.15%]), 76/76 missing attribute routed to Tier 2 (100.0%), MTC conforms against unverified reference: 0.
  - Phase 2: 0/170 false merges ([0.00%, 2.15%]), 76/76 missing attribute routed to Tier 2 (100.0%), MTC conforms against unverified reference: 0. All gates PASS.
- **Dependencies Pinned**:
  - `pymupdf>=1.24.0` (existing dependency).

---

## Phase 3: Learned Embeddings and Vector Recall

- **What was ported**:
  - Bi-encoder training pipeline `scripts/train_biencoder.py` adapted from B's `machine_learning/train_biencoder.py` with leakage-safe canonical grouping (`split_pairs_by_canonical`), IR metrics computation (`Recall@1`, `Recall@5`, `Recall@10`, `MRR@10`), and dual loss architecture (`MultipleNegativesRankingLoss` for positive pairs, `TripletLoss` for hard-negative triplets).
  - Neural embedding wrapper `LearnedEmbeddingProvider` in `api/ml/subvectors.py` behind A's existing subvector interface (`dim`/`met`/`pt`/`std`), with graceful fallback `get_embedding_provider(prefer_learned=True)`, `subvector_texts`, and `encode_subvectors`.
  - Database schema: Alembic migration `db/migrations/versions/0008_pgvector_subvectors.py` creating `item_subvectors` with conditional `embedding vector(384)` / `embedding JSONB` support. Updated `ItemSubvector` and `GoldenSubvector` in `api/models/entities.py`.
  - Hard negative dataset derivation: `scripts/derive_hard_negatives.py` deriving 145 hard-negative training triplets from developer fixtures with zero collision/leakage into the locked evaluation set.
  - Training documentation: `docs/ml_training.md` specifying split rules, loss formulations, hardware requirements, and full training CLI commands.
- **What was changed from B**:
  - Qdrant was completely rejected in favor of PostgreSQL with pgvector (or JSONB fallback).
  - Strict preservation of Invariants S9 & S14: vector recall only retrieves candidates into candidate pool; it can never produce Tier 1 or override a HARD/REQUIRED verdict.
  - Strict dependency isolation: the base install and all tests run without heavy ML dependencies (`sentence-transformers`, `torch`), falling back to deterministic hashed embeddings with visible `ML_MODEL_UNAVAILABLE` flag.
  - Gate honesty: every row in `packs/*/eval/*.csv` is strictly excluded from training data.
- **Tests Added**:
  - `tests/test_vector_recall_safety.py` (9 tests):
    - `test_invariant_s9_s14_vector_recall_cannot_raise_hard_mismatch_to_tier1`: verifies vector recall candidate with 0.985 cosine cannot override Class 150 vs Class 300 mismatch to Tier 1.
    - `test_invariant_s9_s14_vector_recall_cannot_raise_missing_attribute_to_tier1`: verifies vector recall candidate missing required attribute cannot auto-harmonize to Tier 1.
    - `test_learned_encoder_graceful_fallback_without_ml_extra`: verifies graceful fallback with `ML_MODEL_UNAVAILABLE` flag.
    - `test_subvector_texts_extraction`: verifies 4-domain text extraction for dicts and strings.
    - `test_biencoder_leakage_safe_split`: verifies 100% isolation of canonical_id between train and heldout splits.
    - `test_biencoder_retrieval_metrics_calculation`: verifies Recall@k and MRR computation with mock encoder.
    - `test_biencoder_smoke_training_run`: verifies end-to-end smoke training execution.
    - `test_derive_hard_negatives_zero_eval_leakage`: asserts zero collision between derived training pairs and locked eval pairs.
    - `test_subvector_entities_and_optional_vector_storage`: verifies `ItemSubvector` and `GoldenSubvector` entity schema.
  - Total test count: 253 passed (up from 244 in Phase 2, 234 baseline).
- **Eval-Harness Before / After**:
  - Baseline, Phase 1 & Phase 2: 0/170 false merges ([0.00%, 2.15%]), 76/76 missing attribute routed to Tier 2 (100.0%).
  - Phase 3: identical, 0/170 false merges ([0.00%, 2.15%]), 76/76 missing attribute routed to Tier 2 (100.0%). All gates PASS.
- **Dependencies Pinned**:
  - `sentence-transformers>=3.0.0`, `torch>=2.2.0`, `datasets>=2.19.0` in optional extra `ml`.

---

## Phase 4: NER

- **What was ported**:
  - NER fine-tuning pipeline `scripts/train_ner.py` adapted from B's `machine_learning/train_ner.py` with character-offset BIO alignment and held-out evaluation.
  - Per-label performance reporting: implemented `compute_per_label_metrics` calculating exact Precision, Recall, and F1 per class from observed confusion counts.
  - Label reconciliation: resolved B's 6 training labels (`ITEM_TYPE`, `SIZE`, `PRESSURE_RATING`, `METALLURGY`, `FACING_END`, `STANDARD`) to A's 12 canonical token classes (`TOKEN_CLASSES`), with context-aware disambiguation of `FACING_END` into `FACING` vs `END_CONN`.
  - Added `LearnedNERExtractor` and `get_ner_extractor` in `api/ml/ner.py` with graceful fallback to regex when fine-tuned weights or transformers dependencies are absent.
  - Added `cross_check_ner_with_deterministic_extractors` enforcing Safety Invariant S12:
    - NER is never the sole source of a HARD or statutory attribute.
    - Disagreement between NER and deterministic extractors penalizes attribute confidence, raises `NER_DETERMINISTIC_DISAGREEMENT`, and NEVER overrides the deterministic extractor.
    - Attributes discovered solely by NER are flagged `NER_UNVALIDATED_BY_DETERMINISTIC_RULES` and capped at low confidence (<= 0.40) to prevent auto-harmonization in Tier 1.
- **What was changed from B**:
  - Resolved B's discrepancy where training data only covered 6 label types despite declaring 25 in documentation.
  - Discarded B's unverified assumption of model authority; NER output is strictly treated as an auxiliary cross-validation signal.
  - All ML dependencies kept in optional extra `ml`, ensuring base installation and all tests execute deterministically.
- **Tests Added**:
  - `tests/test_ner_safety.py` (6 tests):
    - `test_b_to_a_label_reconciliation_mapping`: verifies mapping and disambiguation of B's labels to A's 12 classes.
    - `test_invariant_s12_ner_disagreement_lowers_confidence_never_overrides`: verifies Class 150 vs Class 300 disagreement penalizes confidence and raises disagreement flag without overriding deterministic value.
    - `test_invariant_s12_ner_sole_source_cannot_auto_harmonize`: verifies unbacked NER attributes receive low confidence and unvalidated flag.
    - `test_learned_ner_fallback_without_weights`: verifies fallback to regex tagger with `REGEX_NER_FALLBACK` flag.
    - `test_per_label_metrics_calculation_in_train_ner`: verifies exact P/R/F1 calculation from observed counts.
    - `test_train_ner_smoke_run`: verifies end-to-end smoke training execution.
  - Total test count: 259 passed (up from 253 in Phase 3, 234 baseline).
- **Eval-Harness Before / After**:
  - Baseline through Phase 3: 0/170 false merges ([0.00%, 2.15%]), 76/76 missing attribute routed to Tier 2 (100.0%).
  - Phase 4: identical, 0/170 false merges ([0.00%, 2.15%]), 76/76 missing attribute routed to Tier 2 (100.0%). All gates PASS.
- **Dependencies Pinned**:
  - `transformers>=4.42.0`, `torch>=2.2.0`, `seqeval>=1.2.2` in optional extra `ml`.


