# Samanvay Build Progress Log

This log tracks execution progress across phases and agent sessions. It records what was built, what remains open, and the exact acceptance gate outputs.

---

## Current Status

- **Completed Phase:** Phase 3 (Extractor Core & Spec Registry) / **Module 2**
- **Next Phase:** Phase 4 (Safety Comparator & Tiering Engine) / **Module 3**
- **Date Completed:** 2026-10-11
- **Status:** Phase 3 Accepted



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


