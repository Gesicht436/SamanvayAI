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
