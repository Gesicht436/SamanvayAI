# Test Suite Module (`tests/`)

This directory contains automated unit, integration, and security tests for Samanvay.
All tests run with `uv run pytest`.

---

## 1. Test Suite Index

| Test File | Target Module | What It Verifies |
|---|---|---|
| [test_core_utils.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_core_utils.py) | `api/core/` | Verhoeff check digits, single-digit errors, adjacent transposition detection, Trigram similarity, Jaro-Winkler, and SHA-256 hash chains. |
| [test_auth.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_auth.py) | `api/security/` | HS256 JWT encoding/decoding, expiration handling, and Maker-Checker ($Maker \ne Checker$) rules. |
| [test_routes.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_routes.py) | `api/routers/` | Every API endpoint is audited against the public allow-list; unlisted routes require authentication. |
| [test_database_features.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_database_features.py) | `db/` | PostgreSQL append-only audit trigger (blocks `UPDATE`/`DELETE`), hash linkage, and Row-Level Security isolation across tenant organizations. |
| [test_normalize.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_normalize.py) | `api/services/` | Unicode script detection, Indic transliteration, quote mapping, fastener `STD` gating, and collision token preservation. |
| [test_uom.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_uom.py) | `api/services/` | Controlled UoM vocabulary, scalar conversions, rebar $d^2/162$, IS 808 section lookups, and `MissingConversionAttribute` guards. |
| [test_ingest.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_ingest.py) | `api/services/` | CSV and XLSX parsing, verbatim raw payloads, row error reporting, SHA-256 file hash idempotency, and transactional audit logging. |
| [test_extractors.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_extractors.py) | `api/extractors/` | `ExtractedValue` contract, token-boundary TOML/YAML lexicons, size NB parsing (fractions, inch, mm, DN), pressure class (ASME vs PN), conflict detection, and character evidence spans. |
| [test_pack_registry.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_pack_registry.py) | `packs/`, `api/extractors/` | Sector pack loading (12 specs), identity modes (PARAMETRIC, DRAWING), statutory flags, pack unmounting resilience, and `/extract` API endpoints. |
| [test_safety_invariants.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_safety_invariants.py) | `api/services/` | Hypothesis property tests for Safety Invariants S1-S15 (>=300 examples each), golden verdict matrix test, and deliberate mutation check. |
| [test_comparator_tiering_api.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_comparator_tiering_api.py) | `api/routers/` | Integration tests for `/compare` and `/tier` REST endpoints (exact match, missing/mismatch, directional upgrade, tier routing). |
| [test_deep_parsers.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_deep_parsers.py) | `api/extractors/parsers/` | Unit tests for physical parsers: motors (snap, Ex), transformers (kVA, kV, vector groups), refractory, OTR tyres, and pumps. |
| [test_deep_families_eval.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_deep_families_eval.py) | `packs/`, `api/extractors/` | Evaluation release gate for 6 deep families: 45 fixtures/family, 16 hard-negative pairs/family, zero false merges in Tier 1, and >=90% extraction accuracy. |
| [test_standard_parsers.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_standard_parsers.py) | `api/extractors/parsers/` | Unit tests for physical parsers across standard families: cables, structural steel, rebar, bearings, fasteners, instrumentation, breakers, boiler tubes, conveyor belts, mill rolls, wire ropes, hydraulic hoses, and drawings. |
| [test_standard_families_eval.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_standard_families_eval.py) | `packs/`, `api/extractors/` | Evaluation release gate for 15 standard families: 22 fixtures/family (330 total), 10 adversarial pairs/family (150 total), zero false merges in Tier 1, 100% missing attributes in Tier 2, and >=90% extraction accuracy. |
| [test_classify.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_classify.py) | `api/services/` | Subcategory classification across 21 families, category hints, low-confidence uncertainty flags, and ambiguity handling. |
| [test_candidates_scoring.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_candidates_scoring.py) | `api/services/` | Blocking key generation, 4-stage candidate retrieval (alias, MPN, block, partial), 9-feature extraction, and Platt calibrated probability scoring. |
| [test_lifecycle.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_lifecycle.py) | `api/services/` | Golden master creation with Verhoeff MPNG- codes, status transitions, golden master merging, splitting, attribute correction, and transactional audit logging. |
| [test_cold_start.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_cold_start.py) | `api/services/` | Cold-start catalog deduplication, block clustering by attribute signature, provenance tracking, near-match linking, and markdown reporting. |
| [test_match_api.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_match_api.py) | `api/routers/` | End-to-end `POST /match` endpoint authentication, request validation, candidate scoring, tier assignment, reason codes, and empty database fallback. |
| [test_stewardship.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_stewardship.py) | `api/routers/`, `api/services/` | Stewardship Maker-Checker task proposals, self-approval prevention (403), safety-critical domain tags (403), action execution, feedback capture, and audit logs. |
| [test_eval_gate.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_eval_gate.py) | `scripts/` | Mathematical verification of exact Clopper-Pearson confidence bounds, gate_check hard release gates, 3-baseline comparison, and sector/org parity. |
| [test_docs_ocr.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_docs_ocr.py) | `api/services/docs.py`, `api/services/ocr.py` | Fake and PyMuPDF OCR pipelines, Invariant S5 (low-confidence OCR gating on HARD attributes), Invariant S10 (duplicate detection on hash and invoice_key), and precheck. |
| [test_mtc_conformance.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_mtc_conformance.py) | `api/services/mtc.py` | 17 chemistry elements, decimal comma handling, worked check CE_IIW = 0.390, Invariant S15 (unverified reference never yields CONFORMS), and heat/batch matching with stock lots. |
| [test_life_monitor.py](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/tests/test_life_monitor.py) | `api/services/life.py`, `api/routers/lots.py` | Pure Clock injection, multi-basis remaining life (earliest wins), Invariant S6 (expired/unknown expiry), S7 (usage without events), S8 (monotonicity), and ordered FEFO disposition ladder. |

---

## 2. Manual Testing Guide

Run tests using `uv`:

```powershell
# Run all tests in the repository
uv run pytest tests/ -v

# Run Module 7 stewardship governance and evaluation gate tests
uv run pytest tests/test_stewardship.py tests/test_eval_gate.py -v

# Run Module 6 candidate retrieval, scoring, lifecycle, and match tests
uv run pytest tests/test_classify.py tests/test_candidates_scoring.py tests/test_lifecycle.py tests/test_cold_start.py tests/test_match_api.py -v

# Run safety invariants property suite (Hypothesis >=300 runs each)
uv run pytest tests/test_safety_invariants.py -v

# Run comparator and tiering API integration tests
uv run pytest tests/test_comparator_tiering_api.py -v

# Run only core mathematical tests
uv run pytest tests/test_core_utils.py -v

# Run database integration tests (requires docker compose up -d db)
uv run pytest tests/test_database_features.py -v

# Run authentication and route security tests
uv run pytest tests/test_auth.py tests/test_routes.py -v

# Run text normalization and UoM tests
uv run pytest tests/test_normalize.py tests/test_uom.py -v

# Run master data ingestion tests
uv run pytest tests/test_ingest.py -v
```

---

## 3. Connected Documentation

- [Root README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/README.md): System architecture.
- [api/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/api/README.md): Backend framework.
- [db/README.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/db/README.md): Database migrations.
