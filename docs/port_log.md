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
