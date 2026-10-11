# Samanvay Build Progress Log

This log tracks execution progress across phases and agent sessions. It records what was built, what remains open, and the exact acceptance gate outputs.

---

## Current Status

- **Completed Phase:** Phase 6 (Standard Domain Families) / **Module 5**
- **Next Phase:** Phase 7 (Candidate Generation & Vector Engine) / **Module 6**
- **Date Completed:** 2026-10-11
- **Status:** Phase 6 Accepted



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





