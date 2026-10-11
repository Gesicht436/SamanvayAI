# Samanvay Build Progress Log

This log tracks execution progress across phases and agent sessions. It records what was built, what remains open, and the exact acceptance gate outputs.

---

## Current Status

- **Completed Phase:** Phase 11 (Dashboards, Observability & Hardening) / **Module 10**
- **Next Phase:** Complete / Production Ready
- **Date Completed:** 2026-10-11
- **Status:** Phase 11 Accepted



---

## Phase 1: Foundation Core & Security (Module 0)

### What Was Built
1. **Repository Scaffold & Configuration:**
   - Standard directory layout created (`api/`, `db/`, `packs/`, `docs/`, `scripts/`, `tests/`).
   - Package management configured using `uv` (`pyproject.toml`, `uv.lock`).
   - Operating rules defined in [AGENTS.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/AGENTS.md).
   - Environment configurations written: `.env.example`, `.env`, `docker-compose.yml`, `Makefile`.
   - Documentation suite established with 80% ASD-STE100 in `docs/` (`VERSIONS.md`, `verification.md`, `PROGRESS.md`, `decisions.md`, `open-questions.md`, `limitations.md`, `README.md`).
2. **Core Mathematics & Cryptography (`api/core/`):**
   - `verhoeff.py`: Check digit calculations with dihedral group $D_5$ tables; `MPNG-` 17-character opaque code formatting and validation.
   - `hashchain.py`: Tamper-evident audit chain with deterministic canonical JSON and SHA-256 hash chaining.
   - `trigram.py`: PostgreSQL `pg_trgm`-compatible character trigram similarity and Jaccard scoring.
   - `jaro_winkler.py`: Jaro and Jaro-Winkler string similarity with prefix scaling.
   - Beginner-friendly STE `README.md` with theory and manual testing guides.
3. **Security & Governance (`api/security/`):**
   - `jwt_auth.py`: HS256 JWT encoding, decoding, expiration handling, and FastAPI security dependencies.
   - Maker-Checker invariant enforcement ($Maker \ne Checker$).
   - Domain-tag enforcement for safety-critical operations.
   - STE `README.md` detailing security mechanisms.
4. **Database Architecture & Migrations (`db/`):**
   - PostgreSQL 18 container setup with `pgvector`, `pg_trgm`, `pgcrypto`, `btree_gin` in `docker-compose.yml`.
   - Initial Alembic migration `0001_initial_schema.py` creating Section 9.2 relational tables.
   - Row-Level Security (RLS) policies by `app.current_org` failing closed.
   - Append-only PostgreSQL triggers with transaction advisory lock `pg_advisory_xact_lock(727001)` and SHA-256 chaining.
   - Prohibits UPDATE, DELETE, and TRUNCATE operations on `audit_log`.
   - Seed script `seed_foundations.py` populating 4 CPSE organizations across 4 sectors (`OIL-1`, `POWER-1`, `STEEL-1`, `MINE-1`) and 8 users.
5. **API & Test Suite:**
   - FastAPI app in `api/main.py` with `/health`, `/auth/demo-token`, and `/audit/verify`.
   - 25 unit and integration tests passing in `tests/` (`test_core_utils.py`, `test_auth.py`, `test_database_features.py`, `test_routes.py`).
6. **Developer CLI Tooling (`scripts/` & `api/core/`):**
   - `hashchain_verify.py`: Command-line verifier for the PostgreSQL audit log hash chain (`make audit-verify`).
   - `verify_claims.py`: Static scanner verifying `# VERIFY:` code markers against `docs/verification.md` (`make verify-claims`).
   - `demo_token.py`: Command-line JWT token generator for testing.
   - `audit_imports.py`: Standard-library policy scanner.

### Acceptance Gate Evaluation (Phase 1)

| Check | Requirement | Result | Output / Evidence |
|---|---|---|---|
| 1. Code Quality & Linting | `uv run ruff check .` | **PASS** | `All checks passed!` |
| 2. Clean DB Reset from Empty | `uv run python -m db.reset; uv run alembic upgrade head; uv run python -m db.seed.seed_foundations` | **PASS** | `Database schema successfully reset.`<br>`Running upgrade -> 0001_initial_schema`<br>`Successfully seeded 4 organizations. Successfully seeded 8 users.` |
| 3. Verhoeff Error Detection | 100% single-digit and transposition detection | **PASS** | 5 tests passed in `test_core_utils.py` |
| 4. Audit Log Immutability | UPDATE, DELETE blocked; SHA-256 chain verified | **PASS** | `test_audit_log_triggers_and_immutability` PASSED |
| 5. Row-Level Security | Tenant isolation across 4 CPSE orgs | **PASS** | `test_row_level_security_isolation` PASSED |
| 6. Route Protection Audit | Every route protected or on public allow-list | **PASS** | `test_every_route_is_protected_or_allowed` PASSED |
| 7. Full Test Suite | All tests pass via `uv run pytest` | **PASS** | `25 passed in 0.92s` |

**Gate Status: ACCEPTED**
Suggested tag: `git tag phase-1`

---

## Phase 2: Ingest, Text Normalization & Canonical UoM Engine (Module 1)

### What Was Built
1. **Dictionaries & Reference Data (`dictionaries/`):**
   - `abbreviations.json`: Category-gated abbreviations (`VALVES`, `FLANGES`, `PIPES`, `MOTORS`, `CABLES`, `STEEL`, `FASTENERS`) and general abbreviations.
   - `indic/`: Indic trade transliteration maps (`hi.json`, `ta.json`, `te.json`, `bn.json`).
   - `section_properties.csv`: Structural steel profiles with linear mass ($kg/m$) per IS 808 (`VERIFY-004`).
   - `README.md`: ASD-STE100 reference documentation with theory, collision safety, and verification commands.
2. **Script and Language Detection (`api/services/script_detector.py`):**
   - Unicode code point range detection for 9 Indic scripts and Latin.
   - Frequency-based primary script and language assignment.
   - Flags text with both Latin and Indic characters with `MIXED_SCRIPT`.
3. **Text Normalization Engine (`api/services/normalize.py`):**
   - NFKC normalization and typographical quote standardization (`″`, `”`, `“`, `''` -> `"`, `′`, `’`, `‘` -> `'`).
   - Dimension multiplier standardization (`50 x 50 x 6` -> `50X50X6`).
   - Indic combining marks preservation without destructive regex stripping.
   - Transliterates Indic terms to uppercase English terms.
   - Flags unmapped Indic tokens with `UNKNOWN_INDIC_TOKENS` without dropping them.
   - Category-gated abbreviation expansion with fastener `STD` size gating (`STD M16` -> `STUD M16`; ambiguous `STD` flags `AMBIGUOUS_ABBREVIATION`).
   - Enforces cross-sector token collision guards for `ROLL`, `BELT`, `ST`, `EP`, `T22`, `T91`, `T11`, `TUBE`, `I`, `R`, and `FC`.
4. **Canonical Unit of Measure Engine (`api/services/uom.py`):**
   - Controlled vocabulary: `EA, SET, M, KM, KG, MT, LTR, PAIR, ROLL, DRUM, LOT, 100EA, FT`.
   - Dimension canonical bases: `M` for length, `MT` for mass, `EA` for count, `LTR` for volume.
   - Rebar mass formula: $kg/m = d^2 / 162$.
   - Structural steel IS 808 lookup table integration (`SectionPropertiesRegistry`).
   - Plate mass formula: $kg = t \times w \times l \times 7.85$.
   - Pipe mass formula: $kg/m = (OD - WT) \times WT \times 0.02466$.
   - Fasteners `SET` definition requirement.
   - **Safety Invariant:** Raises `MissingConversionAttribute` and records `MISSING_CONVERSION_ATTRIBUTE` flag; never guesses.
5. **Master Tabular Ingestion Service (`api/services/ingest.py`):**
   - Supports CSV (auto-encoding `utf-8-sig`, `utf-8`, `latin-1`) and Excel XLSX spreadsheets (`openpyxl`).
   - Configurable per-organisation column mapping profiles with default heuristic aliases.
   - Retains verbatim input row in `raw_payload` (JSONB) and row numbers.
   - Idempotent on SHA-256 file hash.
   - Row-level error reporting without silent row drops.
   - Atomic database persistence into `documents` and `raw_items`.
   - Ingest transaction records immutable entry in `audit_log` (Invariant S6).
6. **API Endpoints & Routers (`api/routers/ingest.py`):**
   - `POST /normalize`: Public description normalization endpoint.
   - `POST /uom/convert`: Public UoM canonical conversion endpoint.
   - `POST /ingest/upload`: Authenticated multipart upload for CSV and XLSX masters.
7. **Comprehensive Test Suite & Documentation:**
   - 28 new tests in `tests/test_normalize.py`, `tests/test_uom.py`, and `tests/test_ingest.py`.
   - 53 total passing tests across the entire test suite.
   - Windows asyncio compatibility via `WindowsSelectorEventLoopPolicy`.
   - ASD-STE100 `README.md` created in `api/services/` and updated in `api/routers/`.

### Acceptance Gate Evaluation (Phase 2)

| Check | Requirement | Result | Output / Evidence |
|---|---|---|---|
| 1. Code Quality & Linting | `uv run ruff check .` | **PASS** | `All checks passed!` |
| 2. Table-Driven Tests | Normalizer, UoM, and Ingest test coverage | **PASS** | 53 tests passed in 1.19s |
| 3. Indic Combining Marks | Preserved without destructive regex stripping | **PASS** | `test_indic_transliteration_hindi` & `test_indic_unknown_tokens` PASSED |
| 4. MissingConversionAttribute | Raised on missing physical attributes, never guessed | **PASS** | `test_rebar_conversion_missing_diameter` & `test_plate_conversion_missing_dimensions` PASSED |
| 5. Ingestion Idempotency | Duplicate file hash skips re-insertion cleanly | **PASS** | `test_database_ingest_idempotency_and_audit` PASSED (`is_duplicate=True`) |
| 6. Row-Level Error Reporting | Bad rows reported per row, 0 silent drops | **PASS** | `test_parse_csv_tabular_data` PASSED (`error_rows=1`, `r4.errors=['MISSING_DESCRIPTION']`) |
| 7. Make Check Gate | `make check` (lint + full test suite) | **PASS** | `All checks passed!` & `53 passed in 1.19s` |

**Gate Status: ACCEPTED**
Suggested tag: `git tag phase-2`

---

## Phase 3: Extractor Framework & Spec Registry (Module 2)

### What Was Built
1. **Extractor Foundation & Contract (`api/extractors/base.py`):**
   - `ExtractedValue` dataclass: `value`, `confidence`, `source`, `evidence_span` (and `evidence` alias), `flags`.
   - `none_with(flag, evidence_span)` constructor ensuring unambiguous fail-closed behavior.
   - `BaseExtractor` abstract interface defining `extract(text, category)`.
2. **Lexicon Extractor Engine (`api/extractors/lexicon.py`):**
   - Dual TOML (via stdlib `tomllib`) and YAML (via `pyyaml`) file loader.
   - Token boundary matching with `(?<![A-Z0-9])` and `(?![A-Z0-9])`.
   - Longest-synonym-first matching precedence.
   - Detection of multiple distinct canonical matches returning `EXTRACTION_CONFLICT`.
   - Category-gated searching.
   - Character evidence spans referencing the raw input text.
3. **Physical Attribute Parsers (`api/extractors/parsers/`):**
   - `size_nb.py`: Piping Nominal Bore extractor covering full `NB_BY_INCH` fractional mapping up to 48" (1200 mm), direct DN/NB syntax, schedule notation stripping, reducer primary/secondary sizes, and metric fastener pattern rejection (`# VERIFY: VERIFY-003`).
   - `pressure_class.py`: Pressure class extractor supporting ASME ratings (150 to 2500, forged 800, fittings 2000-9000) and PN ratings (2.5 to 400), prefix/suffix syntax, slash conflict rejection, bare PSI rejection, and non-standard rating detection (`# VERIFY: VERIFY-011`).
4. **Specification Registry & Dispatch Pipeline (`api/extractors/registry.py`):**
   - Pydantic schema validation for subcategory specifications (`SubcategorySpecDef`, `AttributeSpecDef`).
   - Identity modes: `PARAMETRIC`, `OEM_PN`, and `DRAWING`.
   - Attribute roles: `HARD`, `REQUIRED`, `SOFT`, `DIRECTIONAL`.
   - Category-gated attribute extraction dispatch prioritizing Python parsers, then lexicons.
   - Asynchronous PostgreSQL database synchronization (`sync_to_db`) upserting into `subcategory_specs` and `attribute_specs`.
   - Flexible pack directory scanning supporting root directories (`packs/`) or isolated pack paths (`packs/common`).
5. **Sector Domain Packs (`packs/`):**
   - `packs/common`: `valves_gate.yaml`, `pipes.yaml`, `flanges.yaml`, `fasteners.yaml` + TOML lexicons (`body_material.toml`, `end_connection.toml`, `facing.toml`).
   - `packs/power`: `transformers.yaml`, `breakers.yaml`, `boiler_tubes.yaml` (statutory IBR certification).
   - `packs/steel`: `refractory.yaml` (shelf-life tracking), `mill_rolls.yaml` (`DRAWING` identity mode).
   - `packs/mining`: `otr_tyres.yaml` (mandatory expiry tracking).
   - `packs/heavy_eng`: `pumps_centrifugal.yaml`, `made_to_drawing.yaml` (`DRAWING` identity mode).
   - 80% ASD-STE100 `README.md` in every sector pack directory.
6. **FastAPI Endpoints (`api/routers/extract.py`):**
   - `POST /extract`: Description attribute extraction with confidence and evidence spans.
   - `GET /extract/specs`: Summary catalog of all registered subcategory specifications.
   - `GET /extract/specs/{subcategory}`: Detailed specification lookup.
   - `POST /extract/sync`: Protected Maker endpoint to persist specs to PostgreSQL.
7. **Comprehensive Testing Suite:**
   - 12 new tests in `tests/test_extractors.py` and `tests/test_pack_registry.py`.
   - 65 total passing tests across the entire test suite.
   - Principle 1.3.7 pack unmounting resilience verified.

### Acceptance Gate Evaluation (Phase 3)

| Check | Requirement | Result | Output / Evidence |
|---|---|---|---|
| 1. Code Quality & Linting | `uv run ruff check .` | **PASS** | `All checks passed!` |
| 2. Spec Registry Loading | All sector pack specifications load without errors | **PASS** | 12 specifications loaded across 5 sector packs |
| 3. Size Parser Golden Cases | `1-1/2"`, `DN150`, `SCH 40 6"`, `STUD M24X150MM` returning no size | **PASS** | `test_size_nb_extractor_table` PASSED |
| 4. Raw Evidence Spans | Every extracted value contains accurate raw character spans | **PASS** | Spans verified on raw text for size, class, and lexicons |
| 5. Pack Resilience | Unmounting or isolating any pack leaves remaining packs functional | **PASS** | `test_pack_unmounting_resilience` PASSED |
| 6. Verification Markers | `# VERIFY:` code markers registered in verification ledger | **PASS** | `make verify-claims` PASSED (VERIFY-003, VERIFY-011) |
| 7. Full Test Suite | All tests pass via `uv run pytest` | **PASS** | `65 passed in 1.48s` |

**Gate Status: ACCEPTED**
Suggested tag: `git tag phase-3`

---

## Phase 4: Safety Comparator, Tiering Engine & Safety Invariants Suite (Module 3)

### What Was Built
1. **Deterministic Attribute Comparator (`api/services/comparator.py`):**
   - Attribute-by-attribute evaluation returning typed `Verdict` (`EXACT`, `MISSING`, `MISMATCH`, `UPGRADE`).
   - Directional substitution lattices:
     - IEC 60079 hazardous area gas groups: $IIC \ge IIB \ge IIA$ (within Group II surface equipment only).
     - IEC 60079 temperature classes: $T6 \ge T5 \ge T4 \ge T3 \ge T2 \ge T1$.
     - Motor efficiency classes: $IE4 > IE3 > IE2 > IE1 > EFF3$ (IS 12615 / IEC 60034-30-1).
     - Power transformer capacity: candidate rating kVA $\ge$ requirement rating kVA (substitution only).
     - Circuit breaker breaking capacity: candidate breaking kA $\ge$ requirement breaking kA.
     - Pressure class: higher class strictly does not substitute without bolt-circle verification (`MISMATCH`).
   - Group I (underground mining) vs Group II (surface) strict isolation: never equal, never substitutes (Invariant $S11$). Group I exemption for absent gas group and t-class.
   - Comprehensive `ItemComparisonResult` report generation with missing-attribute gap alerts.
2. **Safety Tiering Engine (`api/services/tiering.py`):**
   - Single point of truth for Tier 1 auto-harmonization authorization per spec Section 5.1.
   - Full enforcement of Safety Invariants $S1$ to $S15$:
     - $S1$: No Tier 1 if ANY HARD or REQUIRED attribute is missing or mismatched.
     - $S2$: No Tier 1 if ANY extraction flag is present (`EXTRACTION_CONFLICT`, etc.).
     - $S3$: No Tier 1 if retrieval has `PARTIAL_BLOCK` or `CATEGORY_UNCERTAIN`.
     - $S4$: Changing any one HARD attribute never yields Tier 1.
     - $S5$: Low OCR confidence routes directly to Tier 2 review.
     - $S6$: Expired lot or unknown shelf-life is never Stream A inventory eligible.
     - $S7$: Usage-based lot without usage tracking is never Stream A eligible.
     - $S8$: Adding usage never increases remaining shelf-life.
     - $S9$: Scoring model probability may lower a tier, never raise a gated item to Tier 1.
     - $S10$: Duplicate intake document routes to review; never merges silently.
     - $S11$: Ex Group I and II never equal, never substitutes.
     - $S12$: Missing statutory attribute (IBR, Ex) routes to Tier 2 review.
     - $S13$: In `DRAWING` mode, revision difference is never better than Tier 2 without approved equivalence.
     - $S14$: In `OEM_PN` and `DRAWING` modes, text similarity alone never yields Tier 1.
     - $S15$: MTC never yields `CONFORMS` against unverified reference rows.
   - Strict separation of identity and substitution: directional upgrades route to Tier 2 review for requisition only, never merging master identities.
3. **Static Safety Auditor (`scripts/scan_tier1.py`):**
   - Scans codebase for Tier 1 authorizations outside `tiering.py`.
   - Verified 0 unauthorized Tier 1 leaks across the repository.
4. **FastAPI REST Endpoints (`api/routers/compare.py`):**
   - `POST /compare`: Evaluates deterministic attribute comparison and returns verdicts, mismatch flags, and gap alerts.
   - `POST /tier`: Evaluates all invariant guards and calibrated probability to return authoritative tier decisions.
5. **Safety Invariants Property Test Suite (`tests/test_safety_invariants.py`):**
   - Hypothesis property tests for every invariant $S1$ through $S15$, each executing $\ge 300$ random examples. Zero skips.
   - Golden verdict matrix test checking canonical physical test cases.
   - Deliberate mutation check verifying that disabling Tier 1 invariant gating immediately breaks the test suite.
6. **API Integration Test Suite (`tests/test_comparator_tiering_api.py`):**
   - End-to-end integration tests for `/compare` and `/tier` endpoints covering exact matches, missing attributes, directional upgrades, and tier routing.

### Acceptance Gate Evaluation (Phase 4)

| Check | Requirement | Result | Output / Evidence |
|---|---|---|---|
| 1. Code Quality & Linting | `uv run ruff check .` and `uv run ruff format --check .` | **PASS** | `All checks passed! 87 files already formatted` |
| 2. Hypothesis Invariant Tests | S1 to S15 tested with $\ge 300$ examples each, 0 skips | **PASS** | 15 invariant tests passed in `test_safety_invariants.py` |
| 3. Golden Verdict Matrix | Standard test vectors for exact, missing, mismatch, upgrade | **PASS** | `test_verdict_matrix_golden_cases` PASSED |
| 4. Deliberate Mutation Test | Breaking Tier 1 gating causes immediate test failure | **PASS** | `test_deliberate_mutation_breaks_tier1_suite` PASSED |
| 5. Single Source of Truth for Tier 1 | `scan_tier1.py` reports 0 unauthorized Tier 1 assignments | **PASS** | `0 location(s) outside ['tiering.py']` |
| 6. REST API Integration | `POST /compare` and `POST /tier` endpoints pass integration tests | **PASS** | 6 tests passed in `test_comparator_tiering_api.py` |
| 7. Verification Claims | `# VERIFY:` code markers verified against register | **PASS** | `make verify-claims` PASSED |
| 8. Full Test Suite | All tests pass via `uv run pytest` | **PASS** | `88 passed in 4.09s` |

**Gate Status: ACCEPTED**
Suggested tag: `git tag phase-4`

---

## Phase 5: Deep Flagship Families (Module 4)

### What Was Built
1. **6 Deep Flagship Family Specifications & Lexicons:**
   - Common: `VALVES.GATE` (trim codes 1-16, bonnet styles, operators, NACE, fire-safe) and `MOTORS.EX` (Ex Group I coal vs Group II surface, temp classes T1-T6, mounting B3/B5, TEFC).
   - Power: `POWER.TRANSFORMER` (kVA/MVA, dual cooling, primary/secondary voltages, Dyn11 canonical vector groups, tap changers, winding metallurgy).
   - Steel: `STEEL.REFRACTORY` (shapes, taper dimensions, Al2O3/MgO/C key chemistry, shelf life days, bond systems).
   - Mining: `MINING.OTR_TYRE` (section width, radial vs bias, rim diameter in inches, E3/E4/L5 tread codes, star and ply ratings).
   - Heavy Eng: `HEAVY.PUMP_CENTRIFUGAL` (flow conversions, head in metres, speed RPM, OEM nozzle codes 4X3-10, API 610 classifications, seal plans).
2. **Deterministic Physical Parsers (`api/extractors/parsers/`):**
   - Standard-library rule-based parsers implemented for all physical attributes: `motors.py`, `transformers.py`, `refractory.py`, `otr_tyres.py`, `pumps.py`.
   - IEC motor power snap via standard kW series. Group I coal mine underground exemption per Invariant $S11$.
   - Safety checks: flag `PRESSURE_NOT_HEAD` when pressure units are provided for pump head.
   - Flexible token matching in `LexiconExtractor` for hyphenated and spaced compound terms (`_synonym_regex`).
3. **Fixture Data & Adversarial Hard Negatives:**
   - 45 test fixtures in CSV for each of the 6 deep families (270 fixtures total).
   - 16 adversarial hard-negative test pairs for each family (96 pairs total), testing critical safety differences (voltage swaps, Ex group confusion, dimensional taper, tread codes, nozzle sizing).
   - Standards reference seeds with `verified = false` logged in `packs/*/standards/seed.csv`.
4. **Evaluation and Release Gate (`tests/test_deep_families_eval.py`):**
   - Rigorous evaluation suite running all 270 fixtures and 96 adversarial pairs.
   - Refusal gate: 0 hard-negative false merges reach Tier 1 (100% refusal rate).
   - Missing-attribute gate: 100% of missing-attribute test cases land in Tier 2.
   - Extraction accuracy gate: every family achieves $\ge 90\%$ accuracy (overall 98.0%, exceeding 95% threshold).

### Acceptance Gate Evaluation (Phase 5)

| Check | Requirement | Result | Output / Evidence |
|---|---|---|---|
| 1. Code Quality & Linting | `uv run ruff check .` and `uv run ruff format --check .` | **PASS** | `All checks passed! 94 files left unchanged` |
| 2. Deep Family Fixtures Count | $\ge 40$ fixtures per family across 6 families | **PASS** | `test_deep_families_fixtures_count` PASSED (45 per family) |
| 3. Hard-Negative Pairs Count | $\ge 15$ adversarial pairs per family across 6 families | **PASS** | `test_deep_families_hard_negatives_count` PASSED (16 per family) |
| 4. Extraction Accuracy Gate | $\ge 90\%$ per family, $\ge 95\%$ overall | **PASS** | `VALVES.GATE`: 92.6%<br>`MOTORS.EX`: 100.0%<br>`POWER.TRANSFORMER`: 94.8%<br>`STEEL.REFRACTORY`: 100.0%<br>`MINING.OTR_TYRE`: 100.0%<br>`HEAVY.PUMP_CENTRIFUGAL`: 100.0%<br>**Overall: 98.0% (1976/2017)** |
| 5. Hard-Negative Refusal Gate | ZERO false merges reach Tier 1 (fail closed) | **PASS** | `test_zero_hard_negatives_reach_tier1` PASSED (0 leaks) |
| 6. Missing-Attribute Routing Gate | Missing attribute pairs land 100% in Tier 2 | **PASS** | `test_missing_attribute_cases_land_in_tier2` PASSED |
| 7. Tier 1 Single Source of Truth | `scan_tier1.py` reports 0 unauthorized Tier 1 assignments | **PASS** | `0 location(s) outside ['tiering.py']` |
| 8. Verification Register | All code markers match registered claims | **PASS** | `verify_claims.py`: 11 registered claims, 5 markers |
| 9. Full Test Suite | All tests pass via `uv run pytest` | **PASS** | `110 passed in 4.37s` |

**Gate Status: ACCEPTED**
Suggested tag: `git tag phase-5`

---

## Phase 6: Standard Domain Families (Module 5)

### What Was Built
1. **15 Standard Family Specifications & Lexicons across 5 Sector Packs:**
   - Common Pack:
     - `PIPES.PIPE`: Diameter (NPS/DN), Wall Schedule (`SCH 40/80/XXS`), material metallurgy, manufacturing method (seamless vs welded), pipe end type.
     - `FLANGES.FLANGE`: Nominal Bore, ASME Class (150-2500), flange type (WNRF, SORF, BLRF), bore schedule, facing (RF, RTJ, FF).
     - `CABLES.POWER`: Voltage rating (kV), core count (1C, 3C, 3.5C, 4C), conductor cross-section (sq mm), conductor metal (AL/CU), insulation (XLPE/PVC), armour type.
     - `STEEL.STRUCTURAL`: Section profile (ISMB, ISMC, ISA), standard size notation, steel grade (E250, E350).
     - `STEEL.REBAR`: Rebar diameter (mm), steel strength grade (Fe 500D, Fe 550D), corrosion treatment (TMT, CRS).
     - `BEARINGS.BEARING`: Bearing series/part number (6205, 7210), radial internal clearance (C3, C4, CN), seal/shield configuration (2RS, 2Z, OPEN).
     - `FASTENERS.STUD_BOLT`: Thread metric diameter (M16-M64), fastener length, bolt material grade (B7, B8M, 8.8), companion nut grade (2H, 8).
     - `INSTRUMENTS.TRANSMITTER`: Instrument type (PRESSURE, DIFF_PRESSURE, TEMPERATURE, LEVEL), output protocol (4-20MA HART, FOUNDATION_FIELDBUS), wetted metallurgy (316L SS, HASTELLOY_C).
   - Power Pack:
     - `POWER.BREAKER`: Breaker technology (VCB, SF6, ACB, MCCB), rated voltage (kV), rated normal current (A), rated breaking capacity (kA).
     - `POWER.BOILER_TUBE`: Outside diameter (mm), wall thickness (mm), alloy grade (SA213-T22, SA213-T91), statutory IBR compliance.
   - Steel Pack:
     - `STEEL.CONVEYOR_BELT`: Carcass construction (EP, NN, STEEL_CORD), tensile rating (EP 800/4), belt width (mm), cover grade, fire resistance.
     - `STEEL.MILL_ROLL`: Roll function (WORK_ROLL, BACKUP_ROLL, EDGER_ROLL), drawing identity mode (`DRAWING`).
   - Mining Pack:
     - `MINING.WIRE_ROPE`: Nominal diameter (mm), strand construction (6X36, 6X19), core construction (IWRC, FC), tensile grade (1770, 1960 N/mm2), lay direction.
   - Heavy Engineering Pack:
     - `HEAVY.HYDRAULIC_HOSE`: Specification standard class (100R2AT, 2SN, 4SP), dash size (-8) with bidirectional metric bore inference (DN12), working pressure (bar), end fittings.
     - `HEAVY.MADE_TO_DRAWING`: Drawing identity mode (`DRAWING`) with drawing number, owner, and revision level.
2. **Deterministic Physical Parsers (`api/extractors/parsers/`):**
   - 13 dedicated rule-based parsers implemented with pure standard-library dependencies: `cables.py`, `structural.py`, `rebar.py`, `bearings.py`, `fasteners.py`, `instrumentation.py`, `breakers.py`, `boiler_tubes.py`, `conveyor_belts.py`, `mill_rolls.py`, `wire_ropes.py`, `hydraulic_hoses.py`, `made_to_drawing.py`.
   - Connected directly to central registry dispatch table in `api/extractors/registry.py`.
3. **Synthetic Fixtures & Adversarial Evaluation Generator (`scripts/generate_standard_fixtures.py`):**
   - Automated generator creating 22 fixture rows and 10 adversarial hard-negative test pairs for each of the 15 standard families (330 fixtures, 150 pairs).
   - Unverified standards seeds logged in `packs/*/standards/seed.csv` with `verified = false`.
4. **Evaluation and Release Gate (`tests/test_standard_families_eval.py`):**
   - Refusal gate: ZERO hard-negative false merges reach Tier 1 (100% refusal rate).
   - Missing-attribute gate: 100% of missing-attribute test pairs land in Tier 2.
   - Extraction accuracy: 99.3% overall across all 15 families (exceeding 95% threshold; all families >= 90%).
   - Pack unmounting resilience verified across multi-pack environments.

### Acceptance Gate Evaluation (Phase 6)

| Check | Requirement | Result | Output / Evidence |
|---|---|---|---|
| 1. Code Quality & Linting | `uv run ruff check .` and `uv run ruff format --check .` | **PASS** | `All checks passed!` |
| 2. Standard Families Fixtures Count | $\ge 20$ fixtures per family across 15 standard families | **PASS** | `test_standard_families_fixtures_count` PASSED (22 per family, 330 total) |
| 3. Adversarial Hard-Negative Pairs Count | $\ge 8$ pairs per family across 15 standard families | **PASS** | `test_standard_families_hard_negatives_count` PASSED (10 per family, 150 total) |
| 4. Extraction Accuracy Gate | $\ge 90\%$ per family, $\ge 95\%$ overall | **PASS** | **Overall: 99.3% (3020/3041)**<br>All 15 families $\ge 90\%$ |
| 5. Hard-Negative Refusal Gate | ZERO false merges reach Tier 1 (fail closed) | **PASS** | `test_zero_standard_hard_negatives_reach_tier1` PASSED (0 leaks) |
| 6. Missing-Attribute Routing Gate | Missing attribute pairs land 100% in Tier 2 | **PASS** | `test_standard_missing_attribute_cases_land_in_tier2` PASSED |
| 7. Pack Unmounting Resilience | Isolated pack loading leaves system fully operational | **PASS** | `test_pack_unmounting_resilience` PASSED |
| 8. Tier 1 Single Source of Truth | `scan_tier1.py` reports 0 unauthorized Tier 1 assignments | **PASS** | `0 location(s) outside ['tiering.py']` |
| 9. Verification Register | All code markers match registered claims | **PASS** | `verify_claims.py`: 11 registered claims, 5 markers |
| 10. Full Test Suite | All tests pass via `uv run pytest` | **PASS** | `128 passed in 4.79s` |

**Gate Status: ACCEPTED**
Suggested tag: `git tag phase-6`

---

## Phase 7: Candidate Retrieval, Scoring & Cold-Start Deduplication (Module 6)

### What Was Built
1. **Subcategory Classifier (`api/services/classify.py`):**
   - High-precision keyword and regular expression rules covering all 21 domain material subcategories.
   - Fallback centroid similarity using character token n-grams.
   - Classification uncertainty flags: `CATEGORY_UNCERTAIN` when top confidence < 0.50, and `MULTI_CATEGORY_MATCH` when ambiguous tokens span distinct families.
   - Safety Invariant S3 enforcement: Category ambiguity blocks auto-promotion to Tier 1.
2. **Candidate Retrieval Pipeline (`api/services/candidates.py`):**
   - 4-stage prioritized lookup architecture:
     1. `alias_exact`: Direct match in catalog synonyms and previous mappings.
     2. `mpn_exact`: Exact match on normalized OEM part number or drawing designation.
     3. `block_key`: Deterministic blocking hash (`subcategory:size:rating:material`).
     4. `fuzzy`: Trigram similarity within block, falling back to subcategory with `PARTIAL_BLOCK` flag.
   - Hard cap at 200 candidates per query to guarantee bounded retrieval latency.
   - Both async PostgreSQL database lookup (`retrieve_candidates_db`) and in-memory evaluation (`retrieve_candidates_in_memory`).
3. **Calibrated Scorer & Feature Extraction (`api/services/scoring.py`):**
   - 9 pairwise match features: `attr_agree_ratio`, `n_missing`, `n_mismatch`, `trigram_sim`, `cosine_sim`, `alnum_token_jaccard`, `mpn_exact`, `alias_exact`, `extraction_conf_min`.
   - Sigmoid Platt calibration mapping feature vectors into well-calibrated probabilities $P \in [0.0, 1.0]$.
   - Safety Invariant S9 enforcement: Scoring probabilities can only downgrade candidate tiers (e.g., adding `PROBABILITY_REVIEW_RANGE` for Tier 2 review or dropping to Tier 3); they can NEVER raise a gated item to Tier 1.
4. **Golden Master Lifecycle Management (`api/services/lifecycle.py`):**
   - Formal state machine: `DRAFT` -> `ACTIVE` -> `DEPRECATED`.
   - Permanent 17-character `MPNG-` codes protected by the Verhoeff check digit.
   - Operational master lifecycle commands: `create_golden_master`, `update_master_status`, `merge_golden_masters` (`MERGED_INTO`), `split_golden_master` (`SPLIT_INTO`), `correct_master_attributes`.
   - Reassigns raw items and aliases to target masters upon consolidation.
   - Transactional audit log recording: Every lifecycle action emits an immutable audit event to `audit_log` in the same database transaction.
5. **Cold-Start Deduplication Engine & Scale CLI (`api/services/cold_start.py`, `scripts/cold_start_dedup.py`):**
   - Groups legacy procurement items by `(subcategory, block_key)`.
   - Clusters items by exact `HARD+REQUIRED` attribute signatures into proposed `DRAFT` golden masters.
   - Tracks member raw item provenance, aggregated stock quantities, and inventory values in INR.
   - Identifies subset near-matches differing only by missing attributes and flags them for human review (`needs_review`).
   - High-throughput scale benchmark: processes 10,000 synthetic items in 1.79s (5,601 items/sec).
   - Generates executive Intra-Organisation Deduplication Reports in 80% ASD-STE100.
6. **End-to-End Harmonization Match API (`api/routers/match.py`):**
   - `POST /match` endpoint conforming strictly to specsheet Section 15.1 contract.
   - Orchestrates normalization, classification, attribute extraction, candidate retrieval, deterministic pairwise comparison, calibrated scoring, and safety tier assignment.
   - Returns structured JSON with clean text, detected subcategory, extraction flags, attribute gap alerts, ranked candidates with golden codes, tiers, calibrated probabilities, and attribute verdicts.

### Acceptance Gate Evaluation (Phase 7)

| Check | Requirement | Result | Output / Evidence |
|---|---|---|---|
| 1. Code Quality & Linting | `uv run ruff check .` and `uv run ruff format --check .` | **PASS** | `All checks passed!` |
| 2. End-to-End Match API Contract | `POST /match` conforms strictly to Section 15.1 schema | **PASS** | `tests/test_match_api.py` (5 tests PASSED) |
| 3. Subcategory Classifier Accuracy | Identifies subcategories with ambiguity flags | **PASS** | `tests/test_classify.py` (4 tests PASSED) |
| 4. Candidate Retrieval Pipeline | 4-stage retrieval, blocking keys, and candidate caps | **PASS** | `tests/test_candidates_scoring.py` (3 tests PASSED) |
| 5. Scorer Calibration & Invariant S9 | Feature extraction, Platt scaling, S9 invariant | **PASS** | `test_scoring_invariant_s9` PASSED |
| 6. Golden Master Lifecycle & Audit | State transitions, merge/split, Verhoeff codes | **PASS** | `tests/test_lifecycle.py` (5 tests PASSED) |
| 7. Cold-Start Scale Benchmark | High-throughput deduplication at scale (>1,000 items/sec) | **PASS** | `scripts/cold_start_dedup.py --count 10000`:<br>**10,000 items in 1.79s (5,601.2 items/sec)**<br>Deduplication rate: 99.8% |
| 8. Tier 1 Single Source of Truth | `scan_tier1.py` reports 0 unauthorized Tier 1 assignments | **PASS** | `0 location(s) outside ['tiering.py']` |
| 9. Verification Register | All code markers match registered claims | **PASS** | `verify_claims.py`: 11 registered claims, 5 markers |
| 10. Full Test Suite | All tests pass via `uv run pytest` | **PASS** | **148 passed in 7.19s** |

**Gate Status: ACCEPTED**
Suggested tag: `git tag phase-7`

---

## Phase 8: Stewardship Governance & Release Evaluation Harness (Module 7)

### What Was Built
1. **Stewardship Governance Service (`api/services/stewardship.py`):**
   - Implements Section 4.7 & 9.4 Maker-Checker governance ($Maker \ne Checker$).
   - 6 supported stewardship proposal kinds: `LINK`, `CREATE_MASTER`, `MERGE`, `SPLIT`, `CORRECT_ATTR`, and `DOC_REVIEW`.
   - Domain-Tag enforcement: Checkers approving safety-critical subcategories (`safety_critical == True`) must possess at least one domain tag of the subcategory's segment (`users.domains`); missing domain tag returns HTTP 403 `DOMAIN_TAG_REQUIRED`.
   - Proposer $\ne$ Approver constraint: Proposer attempting to approve their own task returns HTTP 403 `MAKER_CHECKER_VIOLATION`.
   - Executes lifecycle actions upon approval: updates raw item status to `LINKED`, creates golden masters, merges/splits duplicate catalog entries.
   - Human feedback capture: Every decision records a `FeedbackExample` row (`label=True` on approval, `label=False` on rejection) for downstream model calibration and dictionary suggestion.
   - Transactional audit log recording: Every task proposal, approval, and rejection emits an immutable audit event to `audit_log` in the same database transaction.
2. **Stewardship API Router (`api/routers/tasks.py`):**
   - Authenticated endpoints:
     - `POST /tasks`: Maker creates a task proposal.
     - `GET /tasks`: Lists stewardship queue tasks with state and kind filtering.
     - `GET /tasks/{task_id}`: Retrieves single task details.
     - `POST /tasks/{task_id}/approve`: Checker approves task.
     - `POST /tasks/{task_id}/reject`: Checker rejects task.
3. **Exact Binomial Confidence Interval Engine (`scripts/clopper_pearson.py`):**
   - Pure standard-library implementation of exact Clopper-Pearson binomial confidence intervals.
   - Closed-form zero-failure upper bound calculator: $1 - a^{1/n}$.
   - Sample size calculation utility: computes required trials $n$ to guarantee target bound at 95% confidence.
4. **Hard Release Gate Auditor (`scripts/gate_check.py`):**
   - Automated auditor reading `metrics.json` and enforcing all 5 hard gates:
     1. Hard-negative false merges: exactly 0 observed.
     2. Missing-attribute routing: 100% routed to Tier 2 or lower.
     3. Low-confidence OCR in Tier 1: 0 found.
     4. MTC conforms against unverified reference: 0 found.
     5. Auto-tier precision (dev): $\ge 0.995$ target.
5. **Comprehensive Evaluation Harness & Baseline Comparison (`scripts/eval_harness.py`, `Makefile`):**
   - Side-by-side evaluation of 3 baselines across all 21 material families (170 adversarial hard negatives differing in 1 critical attribute):
     - **Baseline 1 (Token Cosine Similarity):** 115 false merges / 170 (67.6% error rate).
     - **Baseline 2 (Character Trigram Similarity):** 95 false merges / 170 (55.9% error rate).
     - **Baseline 3 (Samanvay Safety Path):** **0 false merges / 170 (0.0% error rate; 95% Clopper-Pearson bound: 2.15%)**.
   - Missing attribute routing: **76/76 routed to Tier 2 (100.0%)** (95% interval: [95.26%, 100.00%]).
   - Auto-tier precision on dev set: **100.00% (600/600)** (95% interval: [99.39%, 100.00%]).
   - **Sector Parity:** Evaluated across 5 sectors (COMMON, POWER, STEEL, MINING, HEAVY_ENG); maximum parity discrepancy is **0.00%**.
   - **Organisation Parity:** Evaluated across 4 CPSE organisations (OIL-1, POWER-1, STEEL-1, MINE-1); maximum parity discrepancy is **0.00%**.
   - Wired into `make eval-gate`.

### Acceptance Gate Evaluation (Phase 8)

| Check | Requirement | Result | Output / Evidence |
|---|---|---|---|
| 1. Code Quality & Linting | `uv run ruff check .` and `uv run ruff format --check .` | **PASS** | `All checks passed! 130 files already formatted.` |
| 2. Maker-Checker Invariant | Proposer approving own task returns HTTP 403 | **PASS** | `test_maker_checker_violation_proposer_cannot_approve` PASSED |
| 3. Domain Tag Access Control | Unauthorized checker approving safety-critical item returns HTTP 403 | **PASS** | `test_domain_tag_enforcement_on_safety_critical` PASSED |
| 4. Task Lifecycle & Feedback | Approval/rejection executes action, logs feedback, writes audit log | **PASS** | `test_checker_approves_task_records_feedback_and_audit` PASSED<br>`test_checker_rejects_task_records_negative_feedback` PASSED |
| 5. Hard-Negative False Merges Gate | Exactly 0 false merges observed on adversarial test pairs | **PASS** | **0/170 observed (0.0%)**; 95% interval [0.00%, 2.15%] |
| 6. Missing-Attribute Routing Gate | 100% of missing-attribute test cases route to Tier 2 | **PASS** | **76/76 routed (100.0%)**; 95% interval [95.26%, 100.00%] |
| 7. Auto-Tier Precision Gate | Dev set auto-tier precision $\ge 99.5\%$ | **PASS** | **100.00% (600/600)**; 95% interval [99.39%, 100.00%] |
| 8. Three Baselines Comparison | Cosine vs Trigram vs Samanvay reported side-by-side | **PASS** | Cosine: 67.6% err; Trigram: 55.9% err; **Samanvay: 0.0% err** |
| 9. Parity Reporting | Sector and organisation parity reported | **PASS** | Sector Discrepancy: **0.00%**; Org Discrepancy: **0.00%** |
| 10. Tier 1 Single Source of Truth | `scan_tier1.py` reports 0 unauthorized Tier 1 assignments | **PASS** | `0 location(s) outside ['tiering.py']` |
| 11. Verification Register | All code markers match registered claims | **PASS** | `verify_claims.py`: 11 registered claims, 5 markers |
| 12. Full Test Suite | All tests pass via `uv run pytest` | **PASS** | **158 passed in 9.21s** |

---

## Phase 9: Core Frontend Web Application (Module 8)

### What Was Built
1. **Next.js 16 (App Router) Architecture (`web/`):**
   - Bootstrapped with React 19, Tailwind CSS v4, TypeScript strict, and Turbopack.
   - Responsive dark-theme engineering design system with OKLCH-based color tokens.
2. **Role-Aware Navigation & Organisation Switcher (`src/components/common/Header.tsx`, `src/lib/auth-context.tsx`):**
   - **No Default Organisation:** Per specification Section 15.0, organisation switcher initializes with no default selection (`Select CPSE Organisation...`), requiring deliberate selection of enterprise context.
   - Role switcher supporting `VIEWER`, `MAKER`, `CHECKER`, and `ADMIN` with active domain tag indicators.
   - Visible **Synthetic Data Banner** (`src/components/common/DemoBanner.tsx`) warning that demo environments run synthetic clusters and expose no proprietary CPSE data.
3. **Standardizer Screen (`src/app/standardizer/page.tsx`):**
   - Material description input with quick 1-click sample chips (Gate valve, Motor Ex, Transformer, OTR Tyre).
   - Normalized text and individual token stream visualization.
   - Detected subcategory badge with confidence score.
   - Extracted technical attributes grid with evidence span character offsets and interactive hover text highlighting.
   - Ranked candidate golden masters with Tier badges (Tier 1 green, Tier 2 amber, Tier 3 red), match probability, reason codes, and "Inspect Diff Matrix" triggers.
4. **Diff Inspector Screen (`src/app/diff/page.tsx`, `src/components/diff/DiffInspector.tsx`):**
   - Visual side-by-side attribute comparison matrix explaining the decision.
   - Strict color coding: Green (`EXACT`), Amber (`MISSING` / `UPGRADE`), Red (`MISMATCH`).
   - Safety Refusal alert banner on HARD attribute mismatch (Tier 3).
   - Safety Routing alert banner on missing required attribute (Tier 2).
   - Specification Compliant banner on Tier 1 exact match.
   - Preset case switcher demonstrating 4 canonical engineering comparison scenarios.
5. **Stewardship Governance Queue Screen (`src/app/queue/page.tsx`, `src/components/queue/TaskQueue.tsx`):**
   - Paginated task queue with filtering by status, task kind, and sector.
   - **Maker-Checker Governance:** Prevents task proposers from approving their own proposals with explicit UI notices.
   - Domain-tag enforcement on safety-critical items.
   - Rapid keyboard shortcuts (`J` next, `K` previous, `A` approve, `R` reject).
   - Approve / Reject modals requiring mandatory engineering rationale and displaying returned transaction audit sequence and SHA-256 hash.
6. **Evaluation Gate & Parity Screen (`src/app/eval/page.tsx`):**
   - Side-by-side comparison of 3 baselines (Cosine 67.6% error vs Trigram 55.9% error vs Samanvay 0.0% error with exact 95% Clopper-Pearson bound $\le 2.15\%$).
   - Checklist for all 5 hard release gates.
   - Sector parity and CPSE organisation parity tables with 0.00% discrepancy.
7. **Testing Suite:**
   - Vitest component and unit test suite: 16 tests passing in 1.67s across 5 test suites (`tests/auth-context.test.tsx`, `tests/standardizer.test.tsx`, `tests/diff-inspector.test.tsx`, `tests/task-queue.test.tsx`, `tests/eval-gate.test.tsx`).
   - Playwright end-to-end integration test suite: 4 tests passing in 2.5s on Desktop Chromium (`e2e/screens.spec.ts`).
   - ESLint: 0 errors, 0 warnings.
   - Full Next.js production build: compiles in 1.3s with all routes statically prerendered.

### Acceptance Gate Evaluation (Phase 9)

| Check | Requirement | Result | Output / Evidence |
|---|---|---|---|
| 1. Code Quality & Linting | `npm run lint` in `web/` | **PASS** | `0 errors, 0 warnings` |
| 2. Production Build | `npm run build` in `web/` | **PASS** | Compiled in 1.3s; all 6 routes prerendered |
| 3. Unit & Component Tests | `npm test` (Vitest) in `web/` | **PASS** | **16 passed across 5 test suites in 1.67s** |
| 4. End-to-End Integration Tests | `npx playwright test` in `web/` | **PASS** | **4 passed in 2.5s** on Desktop Chromium |
| 5. Standardizer Screen Flow | Input, token extraction, evidence spans, candidate ranking | **PASS** | Verified via Playwright and Vitest |
| 6. Diff Inspector Screen Flow | Color badges (`EXACT`, `MISSING`, `MISMATCH`), safety refusal banners | **PASS** | Verified via Playwright and Vitest |
| 7. Stewardship Queue Flow | Paginated queue, filters, Maker-Checker validation, rationale modals | **PASS** | Verified via Playwright and Vitest |
| 8. Organisation Switcher Invariant | Starts with no default selection (`Select CPSE Organisation...`) | **PASS** | `test("Organisation switcher initializes with no default selection")` PASSED |
| 9. Backend Python Test Suite | `uv run pytest tests/` | **PASS** | **158 passed in 9.58s** |

**Gate Status: ACCEPTED**
Suggested tag: `git tag phase-9`

---

## Phase 10: Document Intake, MTC Engine & Life Monitor (Module 9)

### What Was Built
1. **Database Schema & Migrations (`db/migrations/versions/0002_mtc_lots_life.py`):**
   - Tables added: `procurement_lines`, `stock_lots`, `usage_events`, `life_policies`, `life_alerts`, `cert_records`, `grade_reference`, `mtc_results`.
   - Row-Level Security (RLS) enabled on all tenant-partitioned tables.
   - SQLAlchemy ORM models mapped in `api/models/entities.py` and exported via `api/models/__init__.py`.
2. **OCR & Document Intake Pipeline (`api/services/ocr.py`, `api/services/docs.py`, `api/routers/docs.py`):**
   - Channels supported: `UPLOAD`, `CAMERA`, and `PASTE` (`PASTED_TEXT` flag).
   - `PyMuPDFProvider` (`pymupdf==1.28.2`) and `FakeOCRProvider` implementing `OCRProvider` protocol.
   - Invariant $S5$: low OCR confidence (<0.85) on HARD attributes sets attribute value to `None` with `LOW_OCR_CONFIDENCE` flag.
   - Invariant $S10$: duplicate detection on `file_hash` and normalized `invoice_key` (`<gstin>|<invoice_no>|<date>`), warning or blocking silent merges.
   - Pre-procurement duplicate check endpoint (`POST /docs/precheck`) testing line items against existing golden masters without creating entities, appending an audit record.
3. **MTC Certificate Engine (`api/services/mtc.py`, `POST /docs/{id}/mtc`):**
   - 17 chemistry elements parsed with decimal comma handling and percentage out-of-bounds checks.
   - Strict derived calculations:
     - $CE_{IIW} = C + \frac{Mn}{6} + \frac{Cr + Mo + V}{5} + \frac{Ni + Cu}{15}$ (worked test check 0.390).
     - $PREN = Cr + 3.3 \cdot Mo + 16 \cdot N$.
     - Missing constituents are never replaced with zero; returns `CE_INCOMPLETE` or `PREN_INCOMPLETE`.
   - Invariant $S15$: unverified reference row yields `UNVERIFIED_REFERENCE`, never `CONFORMS`.
   - Stock lot updated with `mtc_verified = true` only when evaluation yields `CONFORMS` and heat or batch number matches.
4. **Life Monitor (`api/services/life.py`, `api/routers/lots.py`):**
   - Pure functions with injectable `Clock` (`RealClock`, `SimulatedClock`). Domain functions never call `datetime.now()` directly.
   - Multi-basis remaining life: `SHELF_LIFE_DAYS`, `USAGE_COUNT`, `USAGE_HOURS`. Earliest-ending basis wins ("6 months or 100 parts, whichever first").
   - Invariant $S6$: expired lot or unknown shelf-life on expiry-tracked lot is never `GREEN`, never Stream A eligible (`EXPIRED_OR_UNKNOWN`).
   - Invariant $S7$: usage-based lot without usage events is never `GREEN` (`NO_USAGE_EVENTS`).
   - Invariant $S8$: recorded usage and advancing time monotonically degrade remaining life.
   - Ordered First-Expired First-Out (FEFO) disposition ladder (`ISSUE_OLDEST_FIRST`, `REDEPLOY_NEAR_EXPIRY`, `VENDOR_RETEST_OR_RETURN`, `DISPOSAL_EXPORT`).
5. **Testing & Verification Suite:**
   - 21 new tests in `tests/test_docs_ocr.py`, `tests/test_mtc_conformance.py`, and `tests/test_life_monitor.py`.
   - Total test suite: 179 passing tests across backend.
   - Release evaluation gate passed: 0 false merges, 100% missing-attribute routing, Clopper-Pearson bound $\le 2.15\%$.

### Acceptance Gate Evaluation (Phase 10)

| Check | Requirement | Result | Output / Evidence |
|---|---|---|---|
| 1. Code Quality & Linting | `uv run ruff check .` and `uv run ruff format --check .` | **PASS** | `All checks passed! 140 files already formatted.` |
| 2. OCR Low-Confidence Gating | Low OCR confidence on HARD attribute sets value to None with flag | **PASS** | `test_invariant_s5_low_ocr_confidence_sets_none` PASSED |
| 3. Document Duplicate Gating | Duplicate document yields warning and routes to review; blocks silent merge | **PASS** | `test_invariant_s10_duplicate_document_blocks_silent_merge` PASSED |
| 4. MTC Chemistry & Formulas | $CE_{IIW}$ worked check 0.390, missing constituents return incomplete | **PASS** | `test_compute_ce_iiw_worked_check` PASSED<br>`test_compute_ce_iiw_missing_constituent_is_incomplete` PASSED |
| 5. Unverified Reference Gating | Invariant S15: Unverified reference row returns `UNVERIFIED_REFERENCE`, never `CONFORMS` | **PASS** | `test_invariant_s15_unverified_reference_never_conforms` PASSED |
| 6. Life Monitor Clock Injection | Pure life functions use injected Clock; no unmocked datetime.now | **PASS** | `test_clock_injection_pure_functions` PASSED |
| 7. Shelf-Life Invariant S6 | Expired or unknown expiry is never GREEN, never Stream A | **PASS** | `test_invariant_s6_expired_lot_never_green` PASSED<br>`test_invariant_s6_unknown_expiry_on_required_never_green` PASSED |
| 8. Usage Tracking Invariant S7 | Usage-based lot without events is never GREEN | **PASS** | `test_invariant_s7_usage_lot_without_events_never_green` PASSED |
| 9. Degradation Monotonicity Invariant S8 | Adding usage and advancing time monotonically degrades life | **PASS** | `test_invariant_s8_usage_and_time_monotonicity` PASSED |
| 10. Multi-Basis Earliest-Wins | Earliest-ending basis determines risk status | **PASS** | `test_multi_basis_earliest_ending_wins` PASSED |
| 11. Full Test Suite | All tests pass via `uv run pytest tests/` | **PASS** | **179 passed in 9.52s** |
| 12. Evaluation Release Gate | All 5 hard release gates pass via `python scripts/eval_harness.py` | **PASS** | **ALL GATES PASSED** (0 false merges, 100% missing-attribute routing) |

**Gate Status: ACCEPTED**
Suggested tag: `git tag phase-10`

---

## Phase 11: Dashboards, Observability & Hardening (Module 10)

### What Was Built
1. **Database Schema & Migrations (`db/migrations/versions/0003_oem_supersession.py`):**
   - Tables added: `oem_part_supersessions`, `oem_catalogue_batches`, `oem_proposals`.
   - Unique constraints: `uq_oem_supersession_mfr_old_pn` on `(manufacturer, old_pn)`.
   - Row-Level Security (RLS) enabled on all tenant-isolated tables with fail-closed policies.
   - SQLAlchemy ORM models mapped in `api/models/entities.py` (`OemPartSupersession`, `OemCatalogueBatch`, `OemProposal`).
2. **Observability & Prometheus Metrics Service (`api/services/observability.py`, `api/routers/metrics.py`):**
   - Thread-safe Prometheus metrics registry supporting Counters, Gauges, and Histograms with non-double-accumulated cumulative bucket rendering.
   - **Privacy Invariant:** Strict validation prohibiting tenant identifiers (`org`, `org_id`), user identifiers (`user_id`, `actor`), and item identifiers (`item_code`, `raw_id`, `description`) in metric labels.
   - Real-time gauge collection from PostgreSQL: review queue depth by domain, active RED risk lots, queued background jobs, audit log record count, and cryptographic hash chain integrity status.
   - Mounted at `GET /metrics`.
3. **Multi-Factor Catalog Health Scorecard (`api/services/health.py`, `api/routers/dashboard.py`):**
   - Multi-factor item completeness per Section 20.1:
     $$\text{item\_completeness} = \frac{\sum \text{weight}(a) \text{ for applicable and unflagged}}{\sum \text{weight}(a)}$$
     with weights: $HARD = 2$, $REQUIRED = 1$, $SOFT = 0$.
   - Evaluates conditional attribute applicability when-conditions (such as `form in [BRICK, PRECAST_SHAPE]`).
   - Non-blended indicators reported separately: classified share, uncertain items count, extraction flag rates, duplicate rate, top missing attributes per subcategory, and statutory missing attributes.
   - Executive dashboard endpoint `GET /dashboard/summary` combining queue depth, tier distribution, harmonization compression ratio, catalog health, OCR readiness, and audit integrity.
4. **OEM Catalogue Onboarding Wizard (`api/services/oem.py`, `api/routers/oem.py`):**
   - Ingests bulk OEM spares catalogue rows with part number normalization and manufacturer name normalization.
   - Automatic supersession mapping: links superseded older part numbers (`OLD-PUMP-01`) to effective new part numbers (`NEWPUMP02`).
   - Generates draft master proposals under `OEM_PN` identity mode with character offset evidence spans.
   - Dual-governance workflow: Maker reviews individual proposals (ACCEPT/REJECT), Checker approves batch with Maker != Checker and domain tag validation.
   - On approval, publishes active Golden Masters and records effective and superseded part number aliases in `golden_aliases`, writing transactional audit records to `audit_log`.
5. **14 Material Clusters Mathematical Calculation & Database Seeding (`scripts/seed_clusters.py`):**
   - Pure mathematical calculations matching Section 19.2 exact rupee spend amounts, pooling classes, table percentages, and scenario savings ranges:
     - Low savings = $0.5 \times \text{table\_pct} \times \text{annual\_spend}$.
     - Base savings = $1.0 \times \text{table\_pct} \times \text{annual\_spend}$.
     - High savings = $1.25 \times \text{table\_pct} \times \text{annual\_spend}$ (capped at 25%).
   - Seeding verified in PostgreSQL: 14 golden masters, 42 raw items, and stock lots created with deliberate safety moments. Offline JSON report exported to `data/seed_clusters_report.json`.
6. **Frontend Web Application Screens (`web/`):**
   - `web/src/app/dashboard/page.tsx`: Executive Dashboard with queue depths by domain, tier distribution, catalog health scorecard, and the complete 14 cluster savings scenario table.
   - `web/src/app/oem/page.tsx`: OEM Catalogue Onboarding Wizard with drag-and-drop / sample upload, proposals table with supersession badges, character offset evidence spans, Maker review, and Checker dual governance approval.
   - `web/src/app/lots/page.tsx`: Stock Lots & Life Monitor with risk status badges (GREEN, AMBER, RED), multi-basis tracking, and First-Expired-First-Out (FEFO) disposition ladder recommendations.
   - `web/src/app/docs/page.tsx`: Document Intake & MTC screen with pre-procurement duplicate precheck, elemental chemistry inputs, $CE_{IIW}$ calculation, ASTM A105 limits verification, and Invariant S15 gating.
   - `web/src/components/common/Header.tsx`: Integrated navigation for all 8 application screens.
7. **Comprehensive Testing Suite:**
   - 13 new backend unit and integration tests passing in `tests/test_observability.py`, `tests/test_catalog_health.py`, `tests/test_oem_onboarding.py`, and `tests/test_seed_clusters.py`.
   - 192 total passing tests across the backend Python test suite.
   - 20 passing unit tests in `web/` (Vitest).
   - 8 passing end-to-end integration tests in `web/` (Playwright on Chromium).
   - Production Next.js build passes with 0 compilation errors and all static routes prerendered.

### Acceptance Gate Evaluation (Phase 11)

| Check | Requirement | Result | Output / Evidence |
|---|---|---|---|
| 1. Code Quality & Linting | `uv run ruff check .` | **PASS** | `All checks passed!` |
| 2. Prometheus Metrics & Privacy | `/metrics` endpoint with zero tenant/item identifiers | **PASS** | `tests/test_observability.py` (4 tests PASSED) |
| 3. Multi-Factor Catalog Health | Section 20.1 completeness (HARD=2, REQ=1, SOFT=0) and non-blended indicators | **PASS** | `tests/test_catalog_health.py` (4 tests PASSED) |
| 4. OEM Onboarding & Supersession | Part normalization, supersession chains, Maker != Checker approval | **PASS** | `tests/test_oem_onboarding.py` (2 tests PASSED) |
| 5. 14 Cluster Calculations & Seeding | Pure mathematical computation of Section 19.2 clusters and financial savings | **PASS** | `tests/test_seed_clusters.py` (3 tests PASSED) |
| 6. Frontend Unit Tests | `npm test` (Vitest) in `web/` | **PASS** | **20 passed across 6 test suites in 1.89s** |
| 7. Frontend E2E Tests | `npx playwright test` in `web/` | **PASS** | **8 passed in 3.4s** on Desktop Chromium |
| 8. Frontend Production Build | `npm run build` in `web/` | **PASS** | Compiled in 659ms; all 9 application routes prerendered |
| 9. Full Python Test Suite | `uv run pytest tests/` | **PASS** | **192 passed in 9.57s** |
| 10. Evaluation Release Gate | All 5 hard release gates pass via `python scripts/eval_harness.py` | **PASS** | **ALL GATES PASSED** (0 false merges, 100% missing-attribute routing) |

**Gate Status: ACCEPTED**
Suggested tag: `git tag phase-11`







