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

---

## Phase 5: Reranker and Explainability

- **What was ported**:
  - XGBoost reranker pipeline `scripts/train_reranker.py` adapted from B's `machine_learning/reranker/train.py`, featuring stratified train/validation split, exact AUC calculation (Mann-Whitney U statistic), and early stopping.
  - Unified ML training runner `scripts/train_all.py` supporting `--smoke` and handling optional dependencies gracefully.
  - Active learning review queue `api/ml/active_learning.py` with uncertainty sampling formula ($u = 1.0 - \min(1.0, 2 \times |\text{prob} - 0.5|)$).
  - Real TreeSHAP explanation provider `TreeSHAPExplainer` in `api/ml/explain.py` extracting exact margins via `booster.predict(matrix, pred_contribs=True)`.
  - Identity-safe feature engineering in `api/ml/rerankers.py`: vectorization (`to_vector()`, `to_dict()`, `feature_names()`) and single shared XGBoost model architecture with categorical `sector_id` feature.
- **What was changed from B**:
  - **Single Shared XGBoost Model with Sector Feature**: We chose a single shared XGBoost model rather than 5 disjoint sector models. The rationale: materials across valves, fittings, pipes, flanges, and gaskets share foundational physical verification mechanics (sizeNB, rating/class, ASTM metallurgy, standards). Pooling all sectors into one shared model gives vastly higher sample density across rare sectors while preventing overfitting. The categorical `sector_id` feature allows trees to learn sector-specific thresholds where required.
  - **Eliminated Non-Identity Rewards**: B had `pressure_upgrade` and positive scores for upgraded metallurgy. In A, identity is not substitution! Higher classes and substitute grades receive negative verdicts (-1.0), never positive match points.
  - **Eliminated Fake Numbers in Explainability**: Replaced A's hardcoded constants in `api/ml/explain.py` with real TreeSHAP contributions when a trained booster is loaded. When none is loaded, the explainer returns an honest `'Attribution unavailable: No trained TreeSHAP model is loaded.'` report preserving the disclaimer header (`DISCLAIMER_TITLE`), emitting zero fake numbers.
  - **Persistent Active Learning Queue**: B had an in-memory `deque` which lost all human corrections on restart. A's implementation persists queue items atomically to `data/active_learning_queue.jsonl` with thread-safe `RLock`.
  - **Tier 1 Exclusion**: Invariant safety rule ensures Tier 1 matches (definitive master identities) are never enqueued for review.
  - **Safety Invariant S9/S14 Enforcement**: Hard attribute mismatches clamp model probability to $\le 0.20$, missing required attributes cap probability to $\le 0.85$, and `assign_tier` strictly routes hard mismatches to Tier 3 regardless of ML probability.
- **Tests Added**:
  - `tests/test_reranker_explain_safety.py` (6 tests):
    - `test_invariant_s9_reranker_never_overrides_hard_mismatch_or_raises_to_tier_1`: verifies reranker probability = 0.99 cannot override hard attribute mismatch to Tier 1 (routes strictly to Tier 3).
    - `test_reranker_features_are_strictly_identity_safe`: scans feature names for forbidden upgrade/substitution reward terms and verifies upgraded class yields negative match feature.
    - `test_sector_reranker_safety_clamp`: verifies physical mismatches clamp output probability $\le 0.20$.
    - `test_treeshap_explainer_honesty_when_no_model_loaded`: asserts explainer returns 'Attribution unavailable' with standard disclaimer header and empty contributions when model is None.
    - `test_treeshap_explainer_computes_real_contributions_when_model_provided`: asserts explainer parses real booster contributions and generates plain text bullets.
    - `test_active_learning_uncertainty_and_persistence`: verifies uncertainty sampling, Tier 1 skip, persistent disk reload, and training example export.
  - Updated `tests/test_ml_layer.py`: verified honest fallback and TreeSHAP attribution with model.
  - Total test count: 265 passed (up from 259 in Phase 4, 234 baseline).
- **Eval-Harness Before / After**:
  - Baseline through Phase 4: 0/170 false merges ([0.00%, 2.15%]), 76/76 missing attribute routed to Tier 2 (100.0%).
  - Phase 5: identical, 0/170 false merges ([0.00%, 2.15%]), 76/76 missing attribute routed to Tier 2 (100.0%). All gates PASS.
- **Dependencies Pinned**:
  - `xgboost>=2.0.0`, `shap>=0.45.0` in optional extra `ml`.

---

## Phase 6: Eval Harness, Real Metrics, and Flange Over-Conservatism

- **What was ported / fixed**:
  - **Flange Over-Conservatism Fix** (`packs/common/specs/flanges.yaml`): Made `rtj_groove` conditional on `facing == RTJ` (`when: "facing == RTJ"`). Previously, regular Raised Face (RF) flanges were unconditionally penalized for lacking `rtj_groove` (which only exists on Ring Type Joint flanges), improperly stranding identical RF flanges in Tier 2. With this fix, regular RF flanges harmonize cleanly to Tier 1 (`ALL_HARD_REQUIRED_EXACT`).
  - **Real Developer Fixtures Execution** (`scripts/eval_harness.py`): Replaced the fraudulent placeholder `auto_tier_tp = total_fixtures` (which merely counted raw fixture rows) with actual end-to-end pipeline execution of all 600 developer fixtures from `packs/*/fixtures/*.csv` through attribute extraction, comparison, and tiering.
  - **Real Held-out Evaluation Set** (`data/eval/holdout_pairs.csv`): Created a 120-pair held-out evaluation dataset (60 positive identity pairs and 60 adversarial hard negative pairs) featuring variations unseen in developer fixtures (DN metric vs imperial inches e.g. DN50 vs 2", reordered tokens, "CL150" vs "150#", abbreviation expansions e.g. "WNRF" vs "WELD NECK RAISED FACE", "SW" vs "SOCKET WELD", "CS" vs "CARBON STEEL").
  - **Evaluation Harness Integration**: `scripts/eval_harness.py` now evaluates the 120-pair held-out dataset, reporting true positive rate, false positive rate, Tier 1 and Tier 2 distribution, and exact Clopper-Pearson confidence intervals alongside developer fixture metrics.
  - **Updated Release Metrics** (`metrics.json`): Real execution results stored with Clopper-Pearson confidence intervals.
- **Tests Added**:
  - `tests/test_eval_gate.py` (3 tests):
    - `test_flange_raised_face_lands_in_tier1`: asserts that two identical Raised Face flanges without `rtj_groove` harmonize into Tier 1 with verdict `ALL_HARD_REQUIRED_EXACT`.
    - `test_holdout_pairs_evaluation_zero_false_merges`: evaluates the 120-pair holdout set and asserts 0 false merges across all 60 adversarial hard negatives.
    - `test_developer_fixtures_actual_execution_metrics`: verifies all 600 developer fixtures are executed end-to-end and auto-tier precision is 100.0%.
  - Total test count: 266 passed in 12.03s.
- **Eval-Harness Before / After**:
  - **Before**:
    - Locked eval set (170 hard negatives): 0/170 false merges (0.00% [0.00%, 2.15%]).
    - Missing attribute (76 cases): 76/76 routed to Tier 2 (100.00% [95.26%, 100.00%]).
    - Auto-tier precision: 100% reported via fake row count (`auto_tier_tp = total_fixtures = 600`), Tier 1 recall unmeasured.
    - Held-out evaluation set: none existed.
    - Raised Face flanges: stranded in Tier 2.
  - **After**:
    - Locked eval set (170 hard negatives): 0/170 false merges (0.00% [0.00%, 2.15%]).
    - Missing attribute (76 cases): 76/76 routed to Tier 2 (100.00% [95.26%, 100.00%]).
    - Real Developer Fixture execution (600 fixtures): 62 promoted to Tier 1, 538 safely routed to Tier 2 review. Measured Auto-Tier Precision: 100.00% (62/62) [94.22%, 100.00%] (gate requirement $\ge 99.50\%$). Tier 1 recall: 10.33% (62/600).
    - Real Held-out set (120 pairs): 0/60 false merges on adversarial negatives (0.00% [0.00%, 5.96%]), 12/60 positive pairs promoted to Tier 1, 48/60 safely routed to Tier 2 review due to incomplete catalog specs.
    - Raised Face flanges: cleanly promoted to Tier 1.
    - All release gates PASS.
- **Dependencies Pinned**:
  - No new dependencies required. Standard library CSV and math used.

