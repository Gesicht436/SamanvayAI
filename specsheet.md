# Samanvay: Unified Specification and Build Guide (SIH26099), merged edition

**Problem statement:** AI-Driven Standardization and Harmonization of Material Codes Across CPSEs (Ministry of Petroleum & Natural Gas, Smart India Hackathon 2026).
**Purpose:** a self-sufficient specification for building the project from an empty repository in under 4 weeks, using an AI coding agent (any capable agent; the protocol in section 21 is tool-agnostic). Nothing outside this file is needed. This edition merges the stronger parts of two earlier drafts; see 0.2.

---

## 0. How to use this spec

**Conventions**
- `[VERIFY]`: an external fact (standard number or clause, statutory rule, circular, ERP field length, product specification, software version) that must be checked against a primary source before it reaches a slide or a seed file. Every `[VERIFY]` gets a row in `docs/verification.md`.
- `[ASSUMPTION]`: a modelling input, not a fact. Shown as a range in the UI.
- `[P0]`, `[P1]`, `[P2]`: priority tiers (section 2). Build in tier order; cut from the bottom.
- Every number in the demo is produced by a script from seed data. Never hand-type totals.

**Operating rules for the coding agent** (copied into the repository's `AGENTS.md`, section 22.3)
1. Read `AGENTS.md`, then the section of this spec for the current phase (section 21). Work on one phase per session and stop at its gate.
2. Never invent external facts: standards, clause numbers, statutory rules, ERP field lengths, product data, library versions. Mark them `[VERIFY]` and add a row to `docs/verification.md`.
3. Resolve library and image versions with `uv` and `pnpm` at install time (latest stable) and record them in `docs/VERSIONS.md`. Never pin from memory.
4. Write tests before the families they cover. Property tests are never skipped, loosened or deleted to make a build pass.
5. The safety invariants (section 6) are never relaxed. If a requirement appears to conflict with one, stop and write the conflict in `docs/open-questions.md`.
6. Prefer data to code: a new family, attribute value or abbreviation is a YAML edit. Write Python only where parsing logic is real.
7. Every state change writes an audit record in the same database transaction.
8. Commit small, per task, with a clear message; run `make check` before every commit.
9. When the conversation grows long, write progress and open items to `docs/PROGRESS.md` and continue from that file.
10. If the spec is silent, choose the simpler design and record it in `docs/decisions.md`.

---

### 0.1 Architecture at a glance

```
 Browser (Next.js): dashboard, standardizer, diff inspector, stewardship queue, document intake
                    (upload, camera, paste), MTC panel, lots and alerts, health card, locator, tender, audit
        |  REST/JSON  (OpenAPI contract -> generated TypeScript types), JWT, Prometheus /metrics
        v
 FastAPI + worker (one codebase)
 +--------------------------------------------------------------------------------------------+
 | INTAKE    upload / camera / paste -> text layer or OCR providers -> page classifier         |
 |           -> line + table parse -> MTC engine (chemistry, mechanical, CE, PREN, conformance)|
 | PIPELINE  ingest -> normalize -> extract (YAML + parsers; optional LLM / NER)               |
 |           -> classify (rules, centroid, UNSPSC / GeM map) -> candidates (alias, OEM P/N,    |
 |           block, fuzzy, optional subvector recall) -> compare + tier (S1..S15)              |
 |           -> score (rule / calibrated LR; optional XGBoost; may only LOWER a tier)          |
 | GOVERN    maker-checker stewardship -> golden lifecycle -> aliases -> hash-chained audit    |
 | PUBLISH   ERP cross-reference export, pools + tender pack, surplus and spare locator        |
 | LIFE      lots, policies, risk, alerts, disposition ladder (injectable clock)               |
 +--------------------------------------------------------------------------------------------+
        |
        v
 PostgreSQL 18 only: relational + pgvector + pg_trgm + RLS + audit chain + jobs queue
```

| Decision | Choice | Reason |
|---|---|---|
| Datastore | PostgreSQL with pgvector; no separate vector DB, graph DB or Redis | One backup, one security model, audit written in the same transaction as the change, runs offline |
| Identity | Comparator over typed attributes decides; similarity scores only rank and may only lower a tier | A 0.96 cosine between Class 150 and Class 300 is the failure this project exists to prevent |
| Code | Opaque, permanent `MPNG-` code with Verhoeff check digit | Reclassifying or merging must never change a code |
| ML | Optional layer (8.1) behind gates, measured against the rule-based path | The product is complete and safe without it; it is added only if it measurably helps |
| Explanations | Deterministic per-attribute diff decides; model attribution is a separate, labelled panel | The diff is exactly faithful to the decision; model attribution is not |
| Claims | Every external fact is `[VERIFY]`, every model input is `[ASSUMPTION]` | A hackathon jury and a vigilance auditor will both ask for sources |

### 0.2 Merge ledger (where each part came from)

This edition keeps the first specification (Spec A) as the spine and ports the parts of the second (Spec B, Samanvay-AI v3.0) that were stronger. Numbers refer to the comparison table.

| Taken from Spec B | Where it lives now | Comparison # |
|---|---|---|
| UNSPSC and GeM category mapping | 4.4, 9.2 (`taxonomy_map`, two columns on `golden_masters`), 12 | 6 |
| Home dashboard | 15 (additions), 15.2 | 10 |
| Multi-domain subvector retrieval, BGE-M3 | 8.1 (a), 4.5 (5) | 12, 13 |
| DeBERTa NER extractor, XGBoost sector rerankers | 8.1 (b), 8.1 (c) | 12 |
| TreeSHAP attribution | 8.1 (d) | 24 |
| OCR pipeline detail (300 DPI, deskew, denoise, Paddle + Easy fallback, tables) | 10.1 | 25 |
| MTC chemistry and mechanical engine, CE, PREN | 10.2 | 27 |
| Separate MTC document type, camera capture, paste text | 10, 10.1, 15 | 28 |
| Spare locator with map and distance filters (Postgres, no graph DB) | 13.2 | 35 |
| Prometheus observability | 15.2 | 43 |
| JSON request and response examples | 15.1 | 44 |
| Architecture diagram and decision table, runnable Verhoeff code | 0.1, 9.1 | 55, 7 |

Deliberately **not** carried over from Spec B: Qdrant, Neo4j and Redis (one datastore instead); the semantic code format; the 4-tier scheme and fixed 0.85 / 0.60 thresholds; "upgrade" features that treat a higher class or better metallurgy as a match; the "DPE/CVC statutory pricing formula" wording (the formula is a configurable `[ASSUMPTION]`); the claim that the audit log "meets statutory requirements"; hard-coded secrets and exposed datastore ports; and the numeric ASTM limit table (it could not be confirmed, so numbers are entered by a verifier, see 10.2).

---

## 1. Product definition

### 1.0 Problem statement and traceability

**Background.** Central Public Sector Enterprises (CPSEs) in oil and gas, power, steel, mining and heavy engineering buy and maintain many similar or functionally equivalent materials, but each assigns its own material code, description, specification, unit of measure and classification. The result is duplicate material masters, inconsistent descriptions, hard-to-find equivalents, fragmented procurement data, higher inventory and little collaborative procurement.

**Required solution.** An AI-driven Unified Material Master platform that analyses material codes, descriptions, specifications, technical parameters and procurement history from several CPSEs' ERP/SAP systems; identifies identical, duplicate, near-duplicate and functionally equivalent materials; recommends standardized descriptions, specifications, classifications and a Common National Material Code while keeping the mapping to each CPSE's own codes; lets users review, validate and approve; supports legacy code migration and integration with SAP/ERP; and enables **One Nation, One Material Code** for common materials with traceability to each CPSE code.

| Required capability | Where specified |
|---|---|
| AI-based matching of descriptions and specifications across CPSEs | 4.5, 4.6, 8 |
| Identification of duplicate, near-duplicate and equivalent materials | 4.5, 4.6, 5.2, 8 (cold start) |
| Automated standardization of descriptions and technical attributes | 4.2, 4.3, 7, 18 |
| Intelligent classification and categorization | 4.4, 5, 18 |
| Generation of a Common National Material Code | 9.1 |
| Mapping of existing CPSE codes to the national code | 4.1, 9.2 (`golden_aliases`), 12 |
| Legacy code rationalization and migration support | 4.1, 8 (cold start), 12 (ERP cross-reference) |
| User validation and approval workflow | 4.7, 15 |
| Dashboard for analytics and duplicate detection | 15, 20.1, 13 |
| Audit trail and governance for master changes | 9.4, 4.7 |
| Integration with SAP/ERP systems | 12 |

| Expected impact | How the system shows it |
|---|---|
| Fewer duplicate and redundant codes | cold-start report: "N item codes collapse to M masters" (8) |
| Better data quality | catalog health score before and after (20.1) |
| Better inventory visibility and optimization | surplus matching and life monitor (11, 13) |
| Lower procurement cost through aggregation | pooled demand scenarios (13, 19) |
| Faster specification finalization | pre-procurement duplicate check (10) |
| Inter-CPSE identification and collaboration | cross-organisation matching with disclosure controls (9.3) |
| Foundation for common procurement | golden catalogue, tender pack (13) |

**One-line pitch:** A federated catalogue-harmonization platform that turns each CPSE's messy material master and procurement documents into a shared golden catalogue, never merges safety-critical items on text similarity alone, shows an engineer exactly why two items are or are not the same, and tracks the life of what was bought.

### 1.1 Users
- *Steward / store officer (Maker):* reviews proposals, fixes extraction, reviews documents.
- *Materials manager (Checker):* approves master creation, merges, splits, transfers (never the same person as the maker).
- *Site engineer / procurement officer:* uploads documents, receives life alerts, builds pooled demand.
- *CFO / ministry analyst:* reads the scenario dashboard.
- *Vigilance auditor:* read-only audit access.
- *Domain engineer (a Checker with a domain tag):* holds one or more tags such as POWER, STEEL, MINING, HEAVY_ENG, COMMON. Safety-critical subcategories need a checker with the matching tag (4.7).
- *Platform admin.*

### 1.2 Streams (never mix)
- **Stream A, Surplus redeployment:** idle stock in CPSE X offered against a real requirement in CPSE Y. Value = avoided purchase cost minus transfer cost.
- **Stream B, Forward demand pooling:** future indents from several CPSEs into one tender. Value = scenario-based price effect.
- A unit of stock or demand counts in A or B for a given requirement, never both.

### 1.3 Organisation neutrality principles (design rules)
1. The core is organisation-agnostic. No organisation id literal appears in `api/` logic. Literals are allowed only in seed scripts, fixtures, tests and docs.
2. Per-organisation configuration (`organizations.profile` JSONB): column mapping profile(s), ERP target and field lengths, languages seen, plants, criticality vocabulary, UoM aliases, house abbreviations.
3. No organisation is the pilot, dataset source or reviewer by default. Pilot = one plant of any one participating CPSE, chosen by the team.
4. Tests involving organisations use at least four different organisations from at least four different sectors (oil and gas, power, steel or mining, heavy engineering).
5. Dictionaries are per-language files; Hindi is not special-cased.
6. Domain coverage is tagged by sector segment (1.4).
7. Each sector is a domain pack (section 18). Removing a pack must not break the core or any other pack (tested).

### 1.4 Sector coverage and domain packs
Each subcategory spec carries `segment: COMMON | REFINING | UPSTREAM | MIDSTREAM | MARKETING | PETCHEM | POWER | STEEL | MINING | HEAVY_ENG` (list allowed). The problem statement names Oil & Gas, Power, Steel, Mining and Heavy Engineering; each is covered by a pack (section 18).

| Pack | Families | Deep flagship |
|---|---|---|
| common (oil and gas and cross-sector) | valves, flanges, pipes, fasteners, bearings, instrumentation, motors, cables, structural steel, rebar | valves, motors |
| power | transformers, circuit breakers, boiler tubes | transformers |
| steel | refractories, conveyor belts (shared with mining), mill rolls | refractories |
| mining | OTR tyres, wire ropes (shared), Ex Group I extension | OTR tyres |
| heavy_eng | centrifugal pumps and pump spares, hydraulic hoses, made-to-drawing parts | pumps |

Roadmap only (document, do not build, no invented standards, mark `[VERIFY]`): UPSTREAM (drilling consumables, casing and tubing, wellhead equipment), MIDSTREAM (line pipe, pipeline fittings, compressor spares), MARKETING (LPG cylinders and valves, dispensing equipment, retail-outlet items), PETCHEM and REFINING (catalysts, chemicals, additives; these carry shelf life), and the sector roadmap in 18.8.

### 1.5 Non-goals (say out loud in the pitch)
- Not a replacement for SAP, Oracle or Maximo; not an EAM or full inventory system.
- Not an autonomous merger. The system proposes; humans approve anything safety-critical.
- Does not sell or dispose of anything; it recommends and exports requests.
- Not legal advice on procurement or disposal rules.

---

## 2. Scope tiers, timeline and cut lines (under 4 weeks)

**Tiers**
- **[P0] Core harmonization (must ship):** scaffold, schema, audit, RLS, identity codes, identity modes, normalizer, UoM, YAML extractor engine, spec registry, comparator and tiering with property tests S1 to S15, the `common` pack, the four sector flagships (transformers, refractories, OTR tyres, centrifugal pumps), candidates and scoring, ingest and cold start, stewardship API, minimal UI (standardizer, diff inspector, queue), evaluation baselines, `make demo`.
- **[P1] Differentiators:** document intake, life monitor, the standard-depth families of the new packs, health score card, OEM onboarding wizard, their UI screens, the full-chain demo, evaluation additions, the MTC certificate engine (10.2), the OCR pipeline detail and camera capture (10.1), the home dashboard and Prometheus metrics (15.2).
- **[P2] Completion:** Stream A and B workflows, tender pack, value model, ERP export, CFO dashboard, Hindi UI strings, federated roadmap doc, the spare locator (13.2), UNSPSC/GeM mapping, and the optional ML layer (8.1).

**Domain depth (21 families).** *Deep (6; 40+ fixtures and 15+ hard-negative pairs each, hand-checked by a domain engineer where one is available):* valves, motors (cross-sector, carries Ex Group I/II), transformers, refractories, OTR tyres, centrifugal pumps. Every sector has at least one deep family. *Standard (15; 20+ fixtures and 8+ hard-negative pairs, YAML-driven):* pipes, flanges, cables, structural, rebar, bearings, fasteners, instrumentation, circuit breakers, boiler tubes, conveyor belts, mill rolls, wire ropes, hydraulic hoses, made-to-drawing parts. Pipes and flanges are standard depth so that every sector gets a deep family within the same effort. Report extraction accuracy per family and state the depth.

**Honest feasibility note.** 21 families, document intake, the MTC engine, life monitor, RLS and a hash-chained audit in 28 days leaves no slack. It works only because families are data (YAML plus a few parsers), tests are written first, and the cut order below is applied early rather than at the end. Review this plan weekly against the gates.

**Day plan (4 weeks, one agent session per phase, gate after each)**

| Days | Work | Tier |
|---|---|---|
| 1-2 | Context files, scaffold, schema, audit, RLS, codes, auth, seeds | P0 |
| 3-4 | Normalizer, dictionaries, UoM | P0 |
| 5-6 | Extractor framework, YAML engine, identity modes, spec registry | P0 |
| 7-8 | Comparator, tiering, S1 to S15 property tests (tests before families) | P0 |
| 9-13 | Deep families, one per day with fixtures and hard negatives: valves, motors with Ex I/II, transformers, refractories, OTR tyres, pumps (spread across two days if needed) | P0 |
| 14-16 | Standard families by pack (15 families, YAML-driven) | P0 for the `common` pack, P1 for the rest |
| 17-19 | Embeddings, candidates, scoring, `/match`; ingest, cold start, lifecycle | P0 |
| 20-21 | Stewardship API, feedback, metrics, evaluation harness for all packs | P0 |
| 22-23 | Frontend: P0 screens | P0 |
| 24-25 | Document intake with OCR pipeline (10.1); MTC engine (10.2); life monitor | P1 |
| 26-27 | P1 screens, dashboard, camera capture, Prometheus metrics, health card, OEM wizard, demo seed, hardening | P1 |
| 28 | Docs, rehearsal. Streams, tender pack, value, ERP export, locator, optional ML layer start only if ahead | all |

**Cut order if late:** (0) the optional ML layer (8.1) and the locator map (13.2); (1) P2 streams, tender pack, value and CFO dashboard; (2) Hindi UI and federated doc; (3) scanned-image OCR (keep digital PDFs); (4) usage-based life (keep shelf life) and MTC conformance verdicts (keep extraction and derived values); (5) standard-family fixtures down to 10 each (keep specs and lexicons); (6) the standard families of the new packs (keep the four deep flagships); (7) deep families fall back to standard depth. Never cut: safety invariants, property tests, audit chain, evaluation baselines, the stewardship review step.

---

## 3. Architecture and stack

```
 Sources: CSV/XLSX material masters, ERP extracts   |   Documents: PDF/image (PO, GRN, invoice, datasheet, MTC, label)
        |                                           |
        |                                    [0 Doc Intake] hash, dedup, text layer/OCR, tables, per-line confidence
        +---------------------+---------------------+
                              |
                     [1 Ingest]  parse, provenance, language
                     [2 Normalize]  NFKC, abbreviations (category-gated), transliteration
                     [3 Extract]  YAML lexicon + Python parsers (+ optional LLM) -> typed attributes + confidence
                     [4 Classify]  rules, centroid fallback
                     [5 Candidates]  alias, OEM P/N, block key, fuzzy in block
                     [6 Compare + tier]  per-attribute verdicts -> calibrated probability -> tier
                     [7 Stewardship]  maker-checker, diff inspector, doc review, feedback
                     [8 Publish]  golden lifecycle, aliases, exports, streams, tender pack
                     [9 Life Monitor]  stock lots, life policy, risk, alerts, disposition recommendation
```

**Stack (versions: let `uv`/`pnpm` resolve latest stable at install; record them in `docs/VERSIONS.md`; never pin from memory)**

| Layer | Choice | Note |
|---|---|---|
| Language | Python 3.14 | Use 3.15 only if final, and every dependency installs on it. |
| Package manager | `uv` exclusively | Commit `uv.lock`. |
| Backend | FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2, psycopg 3, pydantic-settings, structlog | |
| Database | PostgreSQL 18 (do not use the 19 beta) with `pgvector`, `pg_trgm`, `pgcrypto`, `btree_gin` | Verify the `pgvector/pgvector:pg18` image tag exists before use. |
| Jobs | Own minimal queue: `jobs` table, `SELECT ... FOR UPDATE SKIP LOCKED`, one worker loop in the same codebase | No Redis, no third-party queue. |
| Embeddings | `intfloat/multilingual-e5-small` (384-dim) via sentence-transformers, local, behind `EmbeddingProvider`; dimension from config | A newer multilingual encoder can replace it via config after measurement. |
| LLM extractor | Optional, behind `LLMExtractor`; local (Ollama-compatible) for air-gapped; a hosted API allowed in dev only; JSON-schema constrained, temperature 0 | Never the sole source for a HARD attribute. |
| Document parsing | PDF text layer first (PyMuPDF); OCR only for scans; `OCRProvider` protocol with Fake, local (Tesseract or similar that installs on 3.14), and optional vision-LLM provider (dev only) | |
| Frontend | Next.js (latest stable, App Router), React (latest stable), TypeScript strict, Tailwind 4, TanStack Table, Recharts, openapi-typescript, Playwright; `pnpm` in `web/` | Check the Node LTS version Next requires. |
| Quality | ruff (lint + format), mypy on `api`, pytest, hypothesis | |
| Packaging | Docker Compose (`db`, `api`, `worker`, `web`) | Offline after one-time pulls. Secrets from `.env`, never in the compose file; only the `web` port is published by default. |
| Observability | `prometheus-client`, `/metrics` (15.2) | Labels never carry organisation or item identifiers. |
| OCR engines | PaddleOCR primary, EasyOCR fallback, Tesseract as last resort, Fake for CI | Candidates only: confirm each installs on the chosen Python `[VERIFY]` (10.1). |
| Image processing | Pillow, NumPy (OpenCV only if it installs cleanly) | Deskew, denoise, autocontrast (10.1). |
| Optional ML (8.1) | `BAAI/bge-m3`, DeBERTa-v3-small, XGBoost, `shap` | Off by default; resolve versions at install. |

**Deployment modes.** (1) Central hub: MoPNG or a neutral host; CPSEs upload. (2) Federated nodes: roadmap; nodes exchange only golden code, descriptor, quantity bucket, contact. Build mode 1; keep schema and RLS compatible with mode 2.

---

## 4. Pipeline stages

### 4.0 Stage 0: Document intake [P1]
See section 10. Output: `doc_lines` that become `raw_items` with `source_type = PROCUREMENT_DOC` and then follow stages 1 to 8 unchanged.

### 4.1 Ingest
- CSV/XLSX through a per-organisation mapping profile (`item_code`, `description`, `long_text`, `uom`, `qty`, `unit_price`, `plant`, `last_movement_date`, `criticality`, `min_stock`, `max_stock`, `manufacturer`, `mpn`).
- Store the original row verbatim (`raw_payload` JSONB), file hash and row number. Never drop a row silently; report errors per row.
- Detect encoding and language per row by Unicode script ranges (Devanagari, Tamil, Bengali, Gujarati, Telugu, Kannada, Malayalam, Odia, Gurmukhi, Latin).
- Idempotent on file hash.

### 4.2 Normalize
1. NFKC; map `″ ” “ ''` to `"` and `′ ’` to `'`.
2. Uppercase Latin; leave Indic scripts.
3. Transliterate Indic trade terms through per-language dictionaries. Unknown Indic tokens stay and lower confidence (`UNKNOWN_INDIC_TOKENS`); mixed Latin+Indic text gets `MIXED_SCRIPT`.
4. Expand abbreviations only inside a candidate category. Unknown category: no expansion of ambiguous tokens.
5. Collapse whitespace; keep `# " ' / - + .` and `X` between numbers. Preserve Indic combining marks (do not use `\w` regex stripping).
6. Output `clean_text`, `tokens`, `language`, `flags`.

Category-gated abbreviations (starter, extendable by stewards and per-org house lists):

| Token | Category | Meaning |
|---|---|---|
| STD | pipes, flanges | standard wall (SCH STD) |
| STD | fasteners | stud, only when followed by a bolt size, else flag |
| FR / FRM | motors | frame |
| FR / FRLS | cables | flame retardant / low smoke |
| GT / GTE | valves | gate |
| GLB | valves | globe |
| CHK / NRV | valves | check / non-return |
| BF | valves | butterfly |
| WN / SO / BL / LJ / SW | flanges | weld neck / slip-on / blind / lap joint / socket weld |
| RF / FF / RTJ | flanges, valves | raised / flat face / ring-type joint |
| SMLS / ERW / BE / PE | pipes | seamless / ERW / bevelled end / plain end |
| HR / CR | steel | hot / cold rolled |
| SS | materials | stainless steel (grade follows) |
| WCB / WC6 / CF8M / LCB | valves, flanges | cast grades, kept as grade tokens |

### 4.3 Extract
Three layers in order: (1) YAML-lexicon and Python rule extractors (section 7); (2) optional LLM extractor and optional NER token classifier (8.1); (3) cross-validator. Per HARD attribute: both agree: confidence 0.95+; one source: 0.70; disagree: null + `EXTRACTION_CONFLICT`; physically invalid: null + flag. Every extracted value carries an evidence span `(start, end, text)`.

### 4.4 Classify
Rules (keyword/regex per subcategory), nearest-centroid fallback on embeddings, low confidence: `CATEGORY_UNCERTAIN`.

**External taxonomy.** Each subcategory may carry an `unspsc_code` and a `gem_category_id`, held in `taxonomy_map` (9.2) and inherited by golden masters. The map is editable data with a `verified` flag; every row starts as `[VERIFY]` and is never generated by a model. ERP export (12) and the tender pack (13) include a code only when `verified`. A missing mapping never blocks matching.

### 4.5 Candidate generation
In order: (1) alias exact; (2) OEM part-number exact; (3) block lookup on `block_key` = hash(category, subcategory, primary dimension value+unit); (4) fuzzy within block, falling back to (category, subcategory) when the block is empty or the primary dimension is NULL, marked `PARTIAL_BLOCK`. (5) [P2, optional] vector recall over the four domain subvectors (8.1), marked `VECTOR_RECALL`; it can only add candidates and never raises a tier. At most 200 candidates. No hard-attribute SQL filters: compare in application code (NULL-safe).

### 4.6 Compare and tier

| Tier | Condition | Action |
|---|---|---|
| 1 Auto-harmonize | All HARD+REQUIRED `EXACT`, no flags, probability >= tau_auto, no alias conflict | Link automatically, log as AUTO |
| 2 Review | Any HARD/REQUIRED missing, any extraction flag (incl. EXTRACTION_CONFLICT, LOW_OCR_CONFIDENCE), probability in [tau_review, tau_auto), PARTIAL_BLOCK, CATEGORY_UNCERTAIN, conflicting alias | Steward task with diff inspector |
| 3 Distinct | Any HARD `MISMATCH`, or REQUIRED `MISMATCH` without steward override | Not the same item |
| Substitution only | One DIRECTIONAL attribute `UPGRADE`, all else `EXACT` | Stream A requisition only, with engineering sign-off; never identity |

### 4.7 Stewardship
Maker proposes (approve link, remap, reject, create master, merge, split, correct attribute, review document line). Checker (different user) approves. Every decision is a `feedback_examples` row feeding scorer retraining and dictionary suggestions (never auto-applied). For `safety_critical` subcategories the Checker must hold the domain tag of the subcategory's segment (`users.domains`); a Checker without it cannot approve. Bulk OEM catalogue onboarding is a steward flow (section 20.2).

### 4.8 Publish
Golden lifecycle, aliases, exports, pooling, transfers, tender pack (sections 9, 13).

### 4.9 Stage 9: Life monitor [P1]
See section 11.

---

## 5. Attribute registry (the safety core)

Implemented as YAML data in `specs/`, loaded and validated at startup, synced to `attribute_specs`.

```yaml
# specs/valves_gate.yaml
subcategory: VALVES.GATE
segment: [COMMON]
primary_dimension: {attr: size_nb, unit: NB_MM}
attributes:
  - {name: size_nb,         role: HARD}
  - {name: pressure_class,  role: HARD}
  - {name: body_material,   role: HARD}
  - {name: end_connection,  role: HARD}
  - {name: facing,          role: HARD, when: "end_connection == FLANGED"}
  - {name: design_standard, role: HARD}
  - {name: trim_code,       role: REQUIRED}
  - {name: bonnet_type,     role: REQUIRED}
  - {name: operator,        role: REQUIRED}
  - {name: fire_safe,       role: REQUIRED}
  - {name: sour_service,    role: REQUIRED}
  - {name: manufacturer,    role: SOFT}
life:                         # optional, see section 11
  - {basis: SHELF_LIFE_DAYS, value: 365, source: "vendor datasheet"}   # VERIFY per item
```

**Roles.** HARD: values equal; different gives Tier 3; missing on either side gives Tier 2. REQUIRED: equal needed for Tier 1; missing gives Tier 2; different gives Tier 3 unless the steward overrides. SOFT: score only. DIRECTIONAL: partial order, used only for substitution.

### 5.1 Starter lists per domain (extend with a domain engineer)

| Domain | HARD | REQUIRED |
|---|---|---|
| Valves | type, size NB, port, pressure class, body material grade, end connection, facing, design standard | trim, bonnet, operator, fire-safe, NACE, temperature range |
| Pipes | size NB, schedule or wall thickness, material spec and grade, manufacturing method, end type | length type, impact test, NACE/HIC, coating |
| Flanges | type, size NB, class or PN, facing and finish, material grade, mating standard, bore schedule (WN) | NACE, RTJ groove |
| Structural | section type and full designation, steel grade and quality, standard and edition | length, tolerance class |
| Rebar | nominal diameter, strength grade, standard | coating, length |
| Motors | rated kW, poles/speed, voltage/frequency, frame, mounting, enclosure/IP, Ex type + gas group + T class + EPL, efficiency class | insulation class, cooling, ambient, duty, VFD-rated |
| Cables | voltage grade, core groups, conductor material, insulation, armour, standard | FRLS, sheath, conductor class, drum length |
| Bearings | base designation, suffix-derived attributes (seal/shield, clearance, cage, precision) | brand-specific suffix verified via xref |
| Fasteners | type, thread standard and size, length, bolt grade, nut grade, coating | set definition, NACE |
| Instrumentation | measured variable, range and unit, output signal, process connection, wetted material, Ex type + gas group + T class | accuracy, display, SIL, mounting |

### 5.2 Identity vs substitution
Identity is equality only: Class 300 is never the same master as Class 150. Substitution asks whether the offered item can serve a requirement; it always needs steward and engineering sign-off.

```
Gas group:  IIC >= IIB >= IIA          (IIC equipment can serve IIB and IIA requirements)
Temp class: T6 >= T5 >= T4 >= T3 >= T2 >= T1   (T6 can serve a T4 requirement)
Ex substitution also needs: same protection type, same or better EPL/zone, ambient covered, valid statutory approval (PESO/CCoE) [VERIFY].
Efficiency: IE4 > IE3 > IE2 > IE1 > legacy EFF3. Higher IE substitutes only if frame, mounting, shaft and electricals are identical.
Metallurgy: an upgrade is a substitution candidate only after corrosion/temperature/NACE and cost review. Never automatic.
Pressure:   a higher class does NOT fit by default (different PCD, bolt count, face-to-face); needs an explicit dimensional check.
```

### 5.3 Identity modes

Not every item is identified by parameters. Each subcategory declares one mode.

| Mode | Identity key | Tier 1 requires | Used by |
|---|---|---|---|
| PARAMETRIC | HARD + REQUIRED attribute signature | all HARD/REQUIRED `EXACT`, no flags (4.6) | most families |
| OEM_PN | normalized (OEM, part number), or an alias | exact key match; text similarity never suffices (S14) | OEM parts, pump spares, brand SKUs |
| DRAWING | normalized (drawing owner, drawing number) plus revision | same key and same revision, or an approved `drawing_revision_equivalence` row (S13) | mill rolls, castings, forgings, fabrications |

Brand-specific refractory grades and tyre SKUs keep a PARAMETRIC master and attach the manufacturer part number as an alias; when only the part number is present they resolve through OEM_PN.

### 5.4 Sector substitution rules (extend 5.2)

```
Ex Group:   Group I (mines) and Group II (surface) are different regimes: never equal, never substitutes. The IIC >= IIB >= IIA lattice applies within Group II only.
Dual Ex:    equipment certified for I and II against a single-group requirement: Tier 2 with both certificates shown.
Transformer: higher kVA is UPGRADE (substitution only). Parallel operation needs same ratio, vector group, compatible impedance [VERIFY].
Breaker:    higher breaking kA at the same voltage and mounting is UPGRADE (substitution only; panel fit and coordination need engineering sign-off).
Boiler tube: a higher-alloy grade is never a default substitute; metallurgy and design-temperature review required. IBR certificate required per lot [VERIFY].
Wire rope:  a higher grade or larger diameter is not a default substitute (design factor); engineering sign-off only.
Pump:       different impeller trim, seal arrangement or material class is a MISMATCH; spares need OEM part number or drawing.
Belt:       FRAS vs non-FRAS is HARD. Underground use needs the fire-resistant class and its approval [VERIFY].
```

---

## 6. Missing data, extraction failure and the safety invariants

Missing HARD attribute: Tier 2 with an attribute-gap alert ("Missing: steel grade, section type"). Conflict: Tier 2 with both values shown. No candidate above tau_review: propose a DRAFT master (cold-start path). Proprietary items: resolve by alias and OEM P/N first; else Tier 2 with a draft `PROP` master.

**Safety invariants (enforced by Hypothesis property tests that run in CI and are never skipped)**
- S1: No Tier 1 if any HARD or REQUIRED attribute is missing or mismatched on either side.
- S2: No Tier 1 if any extraction flag is present (EXTRACTION_CONFLICT, LOW_OCR_CONFIDENCE, NON_STANDARD_RATING, and so on).
- S3: No Tier 1 if `PARTIAL_BLOCK` or `CATEGORY_UNCERTAIN`.
- S4: Changing exactly one HARD attribute never yields Tier 1. Permuting input key order never changes the outcome.
- S5: A HARD attribute extracted from OCR text with confidence below the configured threshold becomes None with `LOW_OCR_CONFIDENCE`.
- S6: An expired lot, or a lot with unknown expiry on a class that requires one, is never GREEN, never Stream A eligible, never auto-issued.
- S7: A usage-based lot with no usage events is never GREEN (status UNKNOWN or INSUFFICIENT_DATA).
- S8: Adding usage never increases remaining life; risk never improves as time advances.
- S9: The scoring model may lower a tier, never raise a gated item to Tier 1.
- S10: A duplicate document warns or blocks; it never merges silently.
- S11: Ex Group I and Group II are never equal and never substitutes in either direction. For Group I, absent `gas_group` and `t_class` are not "missing".
- S12: A `statutory` attribute (for example an IBR certificate, a mine-equipment approval number, an Ex approval) that is missing keeps the item out of Tier 1, Stream A eligibility and auto-issue. Statutory attributes are never inferred from free text alone and never taken from the LLM extractor alone.
- S13: In DRAWING identity mode, Tier 1 requires the same normalized drawing key and the same revision (or an approved equivalence row). A revision difference is never better than Tier 2.
- S14: In OEM_PN and DRAWING identity modes, text similarity alone never yields Tier 1 (the scoring model may lower a tier, never raise a gated item).
- S15: An MTC never yields `CONFORMS` against an unverified reference row, and a lot is marked MTC-verified only by `CONFORMS` plus a heat or batch number match (10.2).

---

## 7. Extractors

**Architecture.** `api/extractors/` has a base interface and two kinds of extractor:
1. **Lexicon extractors (YAML):** `extractors/lexicons/<domain>.yaml` lists, per attribute, canonical values with synonyms and regex patterns, plus validity sets. A single generic engine applies them. Adding a domain or an attribute value is a YAML edit.
2. **Python parsers** only where logic is real: piping size to NB, pressure class, cable core groups, motor ratings, section designations, Ex strings.

Every extractor returns `ExtractedValue(value, confidence, source="rule", evidence_span, flags)`. Category gating is enforced in the registry (subcategory to extractor list), never left to callers. Invalid values become `None` plus a flag, never a guess.

```yaml
# lexicon shape (example)
attribute: body_material
categories: [VALVES, FLANGES]
values:
  A216_WCB: {synonyms: ["WCB", "A216 WCB", "ASTM A216 GR WCB"]}
  A217_WC6: {synonyms: ["WC6", "A217 WC6"]}
  A351_CF8M: {synonyms: ["CF8M", "A351 CF8M"]}
```

### 7.1 Piping size to NB (reference)
```python
import re
from fractions import Fraction

NB_BY_INCH: dict[Fraction, int] = {
    Fraction(1, 8): 6,
    Fraction(1, 4): 8,
    Fraction(3, 8): 10,
    Fraction(1, 2): 15,
    Fraction(3, 4): 20,
    Fraction(1): 25,
    Fraction(5, 4): 32,
    Fraction(3, 2): 40,
    Fraction(2): 50,
    Fraction(5, 2): 65,
    Fraction(3): 80,
    Fraction(7, 2): 90,
    Fraction(4): 100,
    Fraction(5): 125,
    Fraction(6): 150,
    Fraction(8): 200,
    Fraction(10): 250,
    Fraction(12): 300,
    Fraction(14): 350,
    Fraction(16): 400,
    Fraction(18): 450,
    Fraction(20): 500,
    Fraction(22): 550,
    Fraction(24): 600,
    Fraction(26): 650,
    Fraction(28): 700,
    Fraction(30): 750,
    Fraction(32): 800,
    Fraction(34): 850,
    Fraction(36): 900,
    Fraction(40): 1000,
    Fraction(42): 1050,
    Fraction(48): 1200,
}
VALID_NB = set(NB_BY_INCH.values())
SIZE_CATEGORIES = {"VALVES", "PIPES", "FLANGES", "FITTINGS"}
_NUM = r"(?P<n>\d+(?:[\s-]\d+/\d+|\.\d+|/\d+)?)"
RE_INCH = re.compile(_NUM + r'\s*(?:INCHES|INCH|IN\b|"|\'\')')
RE_NB = re.compile(r"(?<![A-Z0-9])(?:DN|NB)\s*(?P<nb>\d{1,4})\b|\b(?P<nb2>\d{1,4})\s*(?:NB|DN)\b")
RE_MM = re.compile(r"(?<![A-Z0-9.])(?P<mm>\d{2,4})\s*MM\b")
RE_SCH = re.compile(r"(?:SCH(?:EDULE)?|SCHD)\s*\.?\s*(?:\d+S?|STD|XS|XXS)")
```
Order: gate by category; strip schedule tokens first; try NB/DN, then inch (via table), then MM only if the value is a valid NB. Reducers (`6X4`): add `size_secondary_nb`, compare as an ordered pair. Required tests: `1-1/2"`, `1 1/2 INCH`, `DN150`, `150NB`, `SCH 40 6"`, and `STUD M24X150MM` in FASTENERS must return no size.

### 7.2 Pressure class (reference)
```python
CLASSES_FLANGED = {150, 300, 600, 900, 1500, 2500}
CLASSES_FORGED = {800}
CLASSES_FITTING = {2000, 3000, 6000, 9000}
RE_CLASS_PREFIX = re.compile(r"(?<![A-Z0-9])(?:CLASS|CLS|CL|RATING|ANSI|ASA)\s*[-.:#]?\s*(?P<c>\d{3,4})(?!\d)")
RE_CLASS_SUFFIX = re.compile(r"(?<!\d)(?P<c>\d{3,4})\s*(?:#|LBS?|LBF)(?![A-Z0-9])")
RE_HASH_PREFIX = re.compile(r"(?<![A-Z0-9])#\s*(?P<c>\d{3,4})(?!\d)")
RE_PN = re.compile(r"(?<![A-Z0-9])PN\s*(?P<pn>\d{1,3})(?!\d)")
```
`ASME_CLASS` and `PN` are different systems and never compare equal. A bare `300 PSI` is not a class.

### 7.3 Cables
Parse core groups with `RE_GROUP = (?P<n>\d+(?:\.5)?)\s*(?P<kind>C|CORE|P|PAIR|T|TRIAD)?\s*[X*]\s*(?P<a>\d+(?:\.\d+)?)` over cases: `4C X 16`, `4CX16 SQMM`, `3.5C X 120`, `3CX95+1CX50`, `3C+E`, `12P X 1.5`. Compare groups as sorted tuples; `3.5C` is its own configuration; an empty parse gives None plus a flag. Voltage `1.1KV`, `1100V`, `650/1100V` map to a `1.1 kV` grade. Also: conductor CU/AL, armour (SWA, GI wire, GI strip, unarmoured), insulation (XLPE, PVC, EPR), FRLS.

### 7.4 Motors
```python
IEC_KW = [
    0.75,
    1.1,
    1.5,
    2.2,
    3,
    4,
    5.5,
    7.5,
    11,
    15,
    18.5,
    22,
    30,
    37,
    45,
    55,
    75,
    90,
    110,
    132,
    160,
    200,
    250,
    315,
    355,
    400,
    450,
    500,
]
HP_TO_IEC = {
    1: 0.75,
    1.5: 1.1,
    2: 1.5,
    3: 2.2,
    5: 3.7,
    7.5: 5.5,
    10: 7.5,
    15: 11,
    20: 15,
    25: 18.5,
    30: 22,
    40: 30,
    50: 37,
    60: 45,
    75: 55,
    100: 75,
    125: 90,
    150: 110,
    200: 150,
}
RPM_TO_POLES = {3000: 2, 1500: 4, 1000: 6, 750: 8}  # 50 Hz synchronous
```
HP maps through `HP_TO_IEC` (75 HP is 55 kW). Do not snap ranges: if not in the table or within 2% of an IEC rating, keep the raw kW and flag `NON_STANDARD_RATING`. `[VERIFY]` the HP table against IS 12615. Poles from `4P`, `4 POLE`, or rpm. Also: voltage, frequency, frame (`250M`, `225S`; `NEMA 326T` is a different frame system, flag), mounting (B3/B5/B35/V1), IP, insulation class, Ex string parsed to `{type, gas_group, t_class, epl}`. Efficiency: `IE1..IE4` and legacy `EFF1..EFF3` are separate attributes; never claim exact equivalence; EFF3 never maps to an IE class.

### 7.5 Other domains (lexicon plus small parsers)
- **Structural:** `ISMB 300`, `ISMC 200`, `ISA 75X75X8`, grade `E250 A|BR|B0|C`, `E350`, legacy `FE410 WA/WB/WC` mapped through `standard_relations` as PARTIAL_EQUIVALENT with a VERIFY flag, length `12M`.
- **Rebar:** `FE 500D`/`FE500D`, `TMT 25MM`, `25 DIA`, coating.
- **Bearings:** base designation (`6312`, `NU 316`, `22212`) plus suffixes (`2Z|ZZ|2RS|2RS1|DDU|C3|C4|M|J|TN9`) through `bearing_suffix_xref` per manufacturer; unknown suffix gives a flag.
- **Fasteners:** `M24X150`, `1"-8 UNC X 6 1/2"`, `ASTM A193 B7`, `A194 2H`, `B7M`, `2HM`; B7 vs B7M and 2H vs 2HM are HARD.
- **Instruments:** `0-10 BAR`, `0-100 KG/CM2`, `4-20MA`, `HART`, wetted `SS316L`, `1/2" NPT(F)`, `Ex ia IIC T4`.

### 7.6 Unit of measure
Controlled vocabulary: `EA, SET, M, KM, KG, MT, LTR, PAIR, ROLL, DRUM, LOT, 100EA, FT`. Canonical base: sections and rebar in MT; cables and pipes in M; equipment in EA. Factors from tables, not per-item rows: rebar `kg/m = d^2/162` (d in mm); sections from `section_properties` (IS 808 `[VERIFY]` each value); plates `thickness_mm * width_m * length_m * 7.85` kg; pipes `(OD - WT) * WT * 0.02466` kg/m. Store original and canonical qty/UoM. A conversion that needs an unknown attribute raises `MissingConversionAttribute` (a flag), never a guess. `SET` for fasteners needs `set_definition`.

### 7.7 Sector parsers
Parsers and lexicons for the families added in section 18 follow the same rules: category gating in the registry, `None` plus a flag on invalid values, an evidence span on every value. The size parser (7.1) runs only for categories in `SIZE_CATEGORIES`; boiler tubes, tyres, belts and ropes use their own parsers. Ex strings (7.4) now parse to `{groups: {I|II}, type, gas_group (II only), t_class (II only), epl}`; see 18.6.3.

---

## 8. Scoring, calibration, cold start, lifecycle

**Features per (raw item, candidate):** `attr_agree_ratio`, `n_missing`, `n_mismatch`, `trigram_sim` on canonical text, `cosine_sim` on canonical text, `alnum_token_jaccard`, `mpn_exact`, `alias_exact`, `extraction_conf_min`.

**Model.** Interpretable rule-based scorer first, labelled "rule-based until trained". Then logistic regression with calibration (Platt or isotonic). `tau_auto` chosen on a dev split for precision >= 99.5% (report observed value and interval). The model may lower a tier, never raise a gated item to Tier 1 (S9). An optional sector-reranker layer (8.1) may replace the logistic regression only if it beats it on the dev split under the same constraint.

**Cold start.** Classify and extract all raw items; group by `block_key`; cluster inside each block by exact HARD+REQUIRED signature; identical signatures become a proposed DRAFT master with member provenance; near-signatures differing only by missing attributes link as `needs_review`; steward tasks `CREATE_MASTER` sorted by cluster size and value. **Intra-organisation dedup report:** "N item codes collapse to M masters", top clusters, stock value tied up in duplicates (first demo moment).

**Golden lifecycle.** `DRAFT -> ACTIVE -> DEPRECATED`; terminal `MERGED_INTO`, `SPLIT_INTO`. Merge moves aliases and raw items and leaves a redirect. Split reassigns raw items; unassigned items return to the queue. Attribute correction goes through maker-checker; the descriptor regenerates; the code never changes.

**Feedback loop.** Every decision writes `feedback_examples`. A retrain script recalibrates the scorer, proposes dictionary entries into a steward-review table (never auto-applied), and reports auto-tier precision over time.

---

### 8.1 Optional ML layer [P2]

**Purpose.** Improve recall on messy text and ranking among candidates. It never decides identity: the comparator and S1 to S15 do. Off by default (`ML_LAYER=off`); the product is complete without it. It is enabled only when it passes the gate at the end of this section.

**(a) Four domain subvectors (recall).** Each golden master and each raw item is encoded as four short texts built from its extracted attributes, so that ratings and sizes do not drown in descriptive words.

| Domain | Contents | Example text |
|---|---|---|
| `dim` | size, schedule, facing, end connection, primary dimension | `size nb mm: 100; end connection: FLANGED; facing: RAISED_FACE` |
| `met` | material grade, product form, coating | `material grade: A216_WCB; product form: CAST` |
| `pt` | pressure class, temperature rating, electrical rating | `pressure class: 150; temperature rating: 200` |
| `std` | design standard, Indian standard, OISD, MESC, EIL references | `standard: API 600; indian standard: IS 1239` |

- Encoder: `BAAI/bge-m3` behind `EmbeddingProvider` (1024 dimensions; dimension from config), compared against the default multilingual-e5-small on the dev split before adoption `[VERIFY model size, licence, language coverage]`.
- Storage: table `golden_subvectors` (9.2) in pgvector, one row per (master, domain), one HNSW index per domain. No external vector database.
- Score: `composite = sum(w_d * cos_d) / sum(w_d)` over active domains; a domain with no extracted attributes gets weight 0 and the rest are renormalized. Weights live in each subcategory YAML as `domain_weights`. Starting weights below are `[ASSUMPTION]` and are tuned on the dev split.

| Family | dim | met | pt | std |
|---|---|---|---|---|
| Valves | 0.30 | 0.30 | 0.25 | 0.15 |
| Pipes and flanges | 0.35 | 0.30 | 0.20 | 0.15 |
| Motors | 0.40 | 0.15 | 0.25 | 0.20 |
| Transformers | 0.45 | 0.15 | 0.20 | 0.20 |
| Structural | 0.50 | 0.35 | 0.00 | 0.15 |
| Refractories | 0.40 | 0.45 | 0.00 | 0.15 |
| OTR tyres | 0.55 | 0.25 | 0.00 | 0.20 |
| Centrifugal pumps | 0.35 | 0.25 | 0.25 | 0.15 |

- Use: candidates found this way are added at stage 5 of 4.5 with the marker `VECTOR_RECALL`. They can only add candidates. They never raise a tier.
- Limitation to state plainly: embeddings handle numbers poorly. A report script prints the measured cosine of a Class 150 versus Class 300 pair under the single-vector and the subvector setup; the number is computed, never typed.

**(b) NER token classifier (optional extractor).** DeBERTa-v3-small with BIO tags, behind an `NERExtractor` interface next to `LLMExtractor`. Classes: ITEM_TYPE, SIZE, PRESSURE, METALLURGY, SCHEDULE, FACING, END_CONN, STANDARD, TRIM, RATING_ELEC, OEM_NAME, OEM_PN (each with B- and I- tags, plus O). Training data: synthetic strings from the noise generator (14) plus steward-confirmed corrections; a training script writes metrics and the model is never in the hot path unless the evaluation shows a gain. Its output counts as one source in the cross-validator (4.3). It is never the sole source for a HARD or statutory attribute (S12).

**(c) Sector rerankers (optional scorer).** XGBoost (`binary:logistic`), five models: common, power, steel, mining, heavy_eng. A sector with too few labelled pairs falls back to the common model, and below that to the rule-based scorer. Features are identity-safe, so no feature rewards a "higher class" or "better metallurgy" as a match:

`composite_cosine`, `dim_cos`, `met_cos`, `pt_cos`, `std_cos`, `item_type_match`, `size_match` (equal, unknown, different), `pressure_match` (equal, unknown, different), `material_match`, `facing_match`, `standard_match`, `attr_coverage`, `n_missing`.

Sector extras (each equality or ratio of the named attributes): power: kVA ratio, HV/LV match, vector group equality, winding material; steel: form equality, Al2O3 ratio, MgO ratio, carbon ratio, bond match; mining: section width ratio, rim match, radial/bias match, tread code equality; heavy_eng: flow ratio, head ratio, pump type equality, seal plan match.

Training: the `eval_pairs` train split, `feedback_examples` and synthetic noise; calibration by Platt or isotonic as in section 8; the model replaces the logistic regression only if it beats it on the dev split. Like every scorer it may lower a tier but never raise a gated item to Tier 1 (S9, S14).

**(d) TreeSHAP attribution.** For the reranker, compute local contributions and show features with absolute contribution above a configured threshold as plain-language bullets. The diff inspector shows them in a separate panel titled "Model score attribution (does not decide the tier)". The deterministic attribute diff stays the explanation of the decision.

**Gate.** The layer ships only if, on the locked test set, recall at 10 improves, hard-negative false merges stay at 0, missing-attribute routing stays at 100%, and auto-tier precision still meets target. Otherwise it stays off and the report says so. Per-sector results are reported with the sector-parity rule of section 14.

---

## 9. Identity, schema, security

### 9.1 Identity
- Code: `MPNG-` + 10-digit sequence + `-` + 1 Verhoeff check digit (17 characters), e.g. `MPNG-0004821937-3`. Opaque, permanent, never reused. Table-driven tests with known Verhoeff vectors and single-digit and transposition error detection. Reference implementation (test vectors computed and checked: `236` gives 3, `12345` gives 1, `0004821937` gives 3, and every single-digit change and adjacent transposition of `00048219373` fails validation):

```python
D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]
INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def check_digit(num: str) -> str:
    c = 0
    for i, d in enumerate(reversed([int(x) for x in num])):
        c = D[c][P[(i + 1) % 8][d]]
    return str(INV[c])


def is_valid(num_with_check: str) -> bool:
    c = 0
    for i, d in enumerate(reversed([int(x) for x in num_with_check])):
        c = D[c][P[i % 8][d]]
    return c == 0
```
- Descriptor (derived, versioned): `VALVES.GATE | 150NB | CL300 | A216-WCB | FLG-RF | API600`.
- Proprietary items: identity key `(normalized OEM, normalized part number)`; revision is an attribute; tags and drawing numbers go to aliases and where-used. `oem_part_supersession(old_pn, new_pn, manufacturer, note)` for supersessions.

### 9.2 Tables (PostgreSQL 18)
Use `gen_random_uuid()`; `uuidv7()` may replace it after verification.

```sql
CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto; CREATE EXTENSION IF NOT EXISTS btree_gin;

CREATE TABLE organizations (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, gstin TEXT, headquarters TEXT,
  segment TEXT[] DEFAULT '{}',
  profile JSONB NOT NULL DEFAULT '{}'   -- mapping profiles, erp_target+field lengths, languages, plants, criticality vocab, uom aliases
);
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id TEXT REFERENCES organizations(id),
  subject TEXT UNIQUE NOT NULL, display_name TEXT, domains TEXT[] DEFAULT '{}',   -- checker domain tags (4.7)
  role TEXT NOT NULL CHECK (role IN ('MAKER','CHECKER','PROCUREMENT','SITE_ENGINEER','CFO','AUDITOR','ADMIN')),
  active BOOLEAN DEFAULT TRUE
);
CREATE TABLE attribute_specs (
  subcategory TEXT NOT NULL, attr TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('HARD','REQUIRED','SOFT','DIRECTIONAL')),
  condition_expr TEXT, order_def JSONB, statutory BOOLEAN DEFAULT FALSE, PRIMARY KEY (subcategory, attr)
);
CREATE TABLE subcategory_specs (
  subcategory TEXT PRIMARY KEY, segment TEXT[] NOT NULL DEFAULT '{}',
  identity_mode TEXT NOT NULL DEFAULT 'PARAMETRIC' CHECK (identity_mode IN ('PARAMETRIC','OEM_PN','DRAWING')),
  safety_critical BOOLEAN DEFAULT FALSE, expiry_required BOOLEAN DEFAULT FALSE,
  pooling_class TEXT CHECK (pooling_class IN ('BULK_MT','BULK_M','ENGINEERED')), depth TEXT CHECK (depth IN ('DEEP','STANDARD'))
);
CREATE TABLE golden_masters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), code TEXT UNIQUE NOT NULL, descriptor TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','ACTIVE','DEPRECATED','MERGED','SPLIT')),
  merged_into UUID REFERENCES golden_masters(id),
  major_category TEXT NOT NULL, subcategory TEXT NOT NULL, block_key TEXT NOT NULL,
  identity_mode TEXT NOT NULL DEFAULT 'PARAMETRIC' CHECK (identity_mode IN ('PARAMETRIC','OEM_PN','DRAWING')), segment TEXT[] DEFAULT '{}',
  attributes JSONB NOT NULL DEFAULT '{}', is_proprietary BOOLEAN DEFAULT FALSE,
  oem_name_norm TEXT, oem_part_number_norm TEXT, canonical_text TEXT NOT NULL,
  embedding VECTOR(384), canonical_uom TEXT NOT NULL,
  unspsc_code TEXT, gem_category_id TEXT,   -- from taxonomy_map, exported only when verified
  created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON golden_masters (block_key);
CREATE INDEX ON golden_masters (oem_name_norm, oem_part_number_norm) WHERE is_proprietary;
CREATE INDEX ON golden_masters USING gin (canonical_text gin_trgm_ops);
CREATE INDEX ON golden_masters USING gin (attributes jsonb_path_ops);
CREATE INDEX ON golden_masters USING hnsw (embedding vector_cosine_ops);

CREATE TABLE golden_aliases (
  id BIGSERIAL PRIMARY KEY, golden_id UUID NOT NULL REFERENCES golden_masters(id),
  alias_type TEXT NOT NULL CHECK (alias_type IN ('CPSE_ITEM_CODE','OEM_PN','DRAWING_NO','MESC','LEGACY_CODE','EQUIPMENT_TAG')),
  org_id TEXT REFERENCES organizations(id), value_raw TEXT NOT NULL, value_norm TEXT NOT NULL,
  UNIQUE (alias_type, org_id, value_norm)
);
CREATE TABLE manufacturers (id SERIAL PRIMARY KEY, name_norm TEXT UNIQUE, names_seen TEXT[]);

CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id TEXT NOT NULL REFERENCES organizations(id),
  doc_type TEXT NOT NULL CHECK (doc_type IN ('PO_GRN','INVOICE','MTC_CERTIFICATE','DATASHEET_LABEL')),
  capture_channel TEXT NOT NULL DEFAULT 'UPLOAD' CHECK (capture_channel IN ('UPLOAD','CAMERA','PASTE')),
  file_hash TEXT NOT NULL, storage_path TEXT NOT NULL, pages INT,
  vendor_gstin TEXT, invoice_no TEXT, invoice_date DATE, invoice_key TEXT,   -- (gstin|invoice_no|date) normalised
  status TEXT DEFAULT 'UPLOADED' CHECK (status IN ('UPLOADED','PARSED','IN_REVIEW','DONE','DUPLICATE','FAILED')),
  uploaded_by UUID REFERENCES users(id), created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (org_id, file_hash)
);
CREATE INDEX ON documents (invoice_key);
CREATE TABLE doc_lines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), document_id UUID NOT NULL REFERENCES documents(id),
  page INT, bbox JSONB, raw_text TEXT NOT NULL, ocr_engine TEXT, raster_dpi INT, ocr_conf NUMERIC(4,3),
  fields JSONB DEFAULT '{}',        -- qty, uom, price, batch_no, mfg_date, expiry_date, po_no, grn_no ...
  raw_item_id UUID
);

CREATE TABLE raw_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id TEXT NOT NULL REFERENCES organizations(id),
  source_type TEXT NOT NULL DEFAULT 'LEGACY_MASTER' CHECK (source_type IN ('LEGACY_MASTER','PROCUREMENT_DOC')),
  doc_line_id UUID REFERENCES doc_lines(id), ocr_conf NUMERIC(4,3),
  source_file_hash TEXT, source_row INT, raw_payload JSONB NOT NULL,
  item_code TEXT, raw_description TEXT NOT NULL, clean_text TEXT, language TEXT,
  original_uom TEXT, original_qty NUMERIC(14,3), canonical_uom TEXT, canonical_qty NUMERIC(14,3),
  unit_price_inr NUMERIC(14,2), plant TEXT, last_movement_date DATE, criticality TEXT,
  min_stock NUMERIC, max_stock NUMERIC, item_condition TEXT DEFAULT 'NEW_UNUSED', has_mtc BOOLEAN DEFAULT FALSE,
  category TEXT, subcategory TEXT, block_key TEXT,
  extracted JSONB DEFAULT '{}', extraction_flags TEXT[] DEFAULT '{}', embedding VECTOR(384),
  golden_id UUID REFERENCES golden_masters(id), tier SMALLINT, match_prob NUMERIC(5,4),
  status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING','AUTO','IN_REVIEW','APPROVED','REJECTED','NEW_MASTER')),
  created_at TIMESTAMPTZ DEFAULT now(), UNIQUE (org_id, item_code, source_file_hash)
);
CREATE INDEX ON raw_items (block_key); CREATE INDEX ON raw_items (golden_id);
CREATE INDEX ON raw_items USING gin (clean_text gin_trgm_ops);

CREATE TABLE match_candidates (
  raw_id UUID REFERENCES raw_items(id), golden_id UUID REFERENCES golden_masters(id),
  verdicts JSONB NOT NULL, features JSONB NOT NULL, prob NUMERIC(5,4), tier SMALLINT,
  PRIMARY KEY (raw_id, golden_id)
);
CREATE TABLE steward_tasks (
  id BIGSERIAL PRIMARY KEY, raw_id UUID REFERENCES raw_items(id),
  kind TEXT CHECK (kind IN ('LINK','CREATE_MASTER','MERGE','SPLIT','CORRECT_ATTR','DOC_REVIEW')),
  payload JSONB NOT NULL, reason_codes TEXT[],
  maker UUID REFERENCES users(id), checker UUID REFERENCES users(id),
  state TEXT DEFAULT 'OPEN' CHECK (state IN ('OPEN','PROPOSED','APPROVED','REJECTED')),
  CONSTRAINT maker_ne_checker CHECK (checker IS NULL OR maker <> checker),
  created_at TIMESTAMPTZ DEFAULT now(), decided_at TIMESTAMPTZ
);
CREATE TABLE feedback_examples (id BIGSERIAL PRIMARY KEY, raw_id UUID, golden_id UUID, label BOOLEAN, features JSONB, steward UUID, created_at TIMESTAMPTZ DEFAULT now());

CREATE TABLE procurement_lines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id TEXT NOT NULL REFERENCES organizations(id),
  golden_id UUID REFERENCES golden_masters(id), doc_line_id UUID REFERENCES doc_lines(id),
  qty NUMERIC(14,3), uom TEXT, unit_price_inr NUMERIC(14,2), vendor TEXT, po_no TEXT, grn_no TEXT, received_on DATE
);
CREATE TABLE stock_lots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id TEXT NOT NULL REFERENCES organizations(id),
  golden_id UUID REFERENCES golden_masters(id), procurement_line_id UUID REFERENCES procurement_lines(id),
  plant TEXT, qty_remaining NUMERIC(14,3), batch_no TEXT, mfg_date DATE, expiry_date DATE, start_date DATE
);
CREATE TABLE usage_events (id BIGSERIAL PRIMARY KEY, lot_id UUID REFERENCES stock_lots(id), ts TIMESTAMPTZ NOT NULL, amount NUMERIC(14,3) NOT NULL, unit TEXT NOT NULL);
CREATE TABLE life_policies (
  id SERIAL PRIMARY KEY, scope_type TEXT CHECK (scope_type IN ('GOLDEN','CLASS')), scope_value TEXT NOT NULL,
  org_id TEXT REFERENCES organizations(id),        -- NULL = global default, set = override
  basis TEXT NOT NULL CHECK (basis IN ('SHELF_LIFE_DAYS','USAGE_COUNT','USAGE_HOURS')),
  limit_value NUMERIC NOT NULL, unit TEXT, source TEXT
);
CREATE TABLE life_alerts (
  id BIGSERIAL PRIMARY KEY, lot_id UUID REFERENCES stock_lots(id), kind TEXT, risk TEXT,
  projected_date DATE, recipient_role TEXT, dedupe_key TEXT UNIQUE,
  state TEXT DEFAULT 'OPEN' CHECK (state IN ('OPEN','ACKED','ESCALATED','CLOSED')), created_at TIMESTAMPTZ DEFAULT now(), acked_at TIMESTAMPTZ
);

CREATE TABLE jobs (
  id BIGSERIAL PRIMARY KEY, kind TEXT NOT NULL, payload JSONB NOT NULL,
  state TEXT DEFAULT 'QUEUED' CHECK (state IN ('QUEUED','RUNNING','DONE','FAILED')),
  attempts INT DEFAULT 0, run_after TIMESTAMPTZ DEFAULT now(), last_error TEXT, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE standards (designation TEXT PRIMARY KEY, body TEXT, title TEXT, scope_note TEXT, edition_year INT,
  status TEXT CHECK (status IN ('ACTIVE','WITHDRAWN','SUPERSEDED')), verified BOOLEAN DEFAULT FALSE, source_url TEXT);
CREATE TABLE standard_relations (id SERIAL PRIMARY KEY, from_std TEXT REFERENCES standards(designation), to_std TEXT REFERENCES standards(designation),
  relation TEXT CHECK (relation IN ('SUPERSEDED_BY','TECHNICALLY_EQUIVALENT','PARTIAL_EQUIVALENT','NOT_EQUIVALENT')), conditions TEXT NOT NULL, year INT, verified BOOLEAN DEFAULT FALSE);
CREATE TABLE section_properties (designation TEXT PRIMARY KEY, kg_per_m NUMERIC(8,3), source TEXT, verified BOOLEAN DEFAULT FALSE);
CREATE TABLE uom_units (code TEXT PRIMARY KEY, dimension TEXT, to_base NUMERIC(18,8), base_unit TEXT);
CREATE TABLE bearing_suffix_xref (manufacturer TEXT, suffix TEXT, attr TEXT, value TEXT, PRIMARY KEY (manufacturer, suffix));
CREATE TABLE brand_grade_xref (manufacturer TEXT, brand_grade TEXT, attr TEXT, value TEXT, source TEXT, verified BOOLEAN DEFAULT FALSE, PRIMARY KEY (manufacturer, brand_grade, attr));
CREATE TABLE drawing_revision_equivalence (id SERIAL PRIMARY KEY, drawing_owner TEXT NOT NULL, drawing_norm TEXT NOT NULL, rev_a TEXT NOT NULL, rev_b TEXT NOT NULL, rationale TEXT NOT NULL,
  proposed_by UUID REFERENCES users(id), approved_by UUID REFERENCES users(id), approved_at TIMESTAMPTZ, CONSTRAINT rev_maker_ne_checker CHECK (approved_by IS NULL OR proposed_by <> approved_by));
CREATE TABLE cert_records (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id TEXT NOT NULL REFERENCES organizations(id), lot_id UUID REFERENCES stock_lots(id), golden_id UUID REFERENCES golden_masters(id),
  cert_type TEXT NOT NULL, cert_no TEXT, issuer TEXT, valid_to DATE, file_hash TEXT, verified BOOLEAN DEFAULT FALSE);   -- IBR certificate, MTC, approval records; types are [VERIFY]
CREATE TABLE forward_indents (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id TEXT REFERENCES organizations(id), golden_id UUID REFERENCES golden_masters(id),
  qty NUMERIC(14,3) NOT NULL, uom TEXT NOT NULL, budget_unit_cost NUMERIC(14,2), need_by DATE NOT NULL, delivery_site TEXT,
  status TEXT DEFAULT 'OPEN' CHECK (status IN ('OPEN','POOLED','ORDERED','CANCELLED')));
CREATE TABLE tender_pools (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), lead_org TEXT REFERENCES organizations(id), golden_id UUID REFERENCES golden_masters(id), status TEXT DEFAULT 'DRAFT', mou_ref TEXT, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE tender_pool_lines (pool_id UUID REFERENCES tender_pools(id), indent_id UUID REFERENCES forward_indents(id), PRIMARY KEY (pool_id, indent_id));
CREATE TABLE transfer_orders (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), from_org TEXT, to_org TEXT, lot_id UUID REFERENCES stock_lots(id), qty NUMERIC(14,3),
  basis TEXT CHECK (basis IN ('BOOK_VALUE','LAST_PURCHASE_PRICE','AGREED')), price NUMERIC(14,2), mtc_uploaded BOOLEAN DEFAULT FALSE, pmi_done BOOLEAN DEFAULT FALSE, shelf_life_ok BOOLEAN, state TEXT DEFAULT 'DRAFT');
CREATE TABLE eval_pairs (id SERIAL PRIMARY KEY, text_a TEXT, text_b TEXT, label BOOLEAN, bucket TEXT, subcategory TEXT, org_a TEXT, org_b TEXT,
  provenance TEXT CHECK (provenance IN ('PUBLIC','SYNTHETIC','STEWARD')), split TEXT);

-- merged-edition tables
CREATE TABLE taxonomy_map (subcategory TEXT PRIMARY KEY REFERENCES subcategory_specs(subcategory), unspsc_code TEXT, gem_category_id TEXT,
  source TEXT, verified BOOLEAN DEFAULT FALSE);                      -- every row [VERIFY]
CREATE TABLE golden_subvectors (golden_id UUID REFERENCES golden_masters(id), domain TEXT CHECK (domain IN ('dim','met','pt','std')),
  embedding VECTOR(1024) NOT NULL, PRIMARY KEY (golden_id, domain));   -- optional ML layer (8.1); dimension from config
CREATE INDEX ON golden_subvectors USING hnsw (embedding vector_cosine_ops) WHERE domain = 'dim';
CREATE INDEX ON golden_subvectors USING hnsw (embedding vector_cosine_ops) WHERE domain = 'met';
CREATE INDEX ON golden_subvectors USING hnsw (embedding vector_cosine_ops) WHERE domain = 'pt';
CREATE INDEX ON golden_subvectors USING hnsw (embedding vector_cosine_ops) WHERE domain = 'std';
CREATE TABLE grade_reference (id SERIAL PRIMARY KEY, grade TEXT NOT NULL, product_form TEXT NOT NULL, property TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('CHEM','MECH')), min_value NUMERIC, max_value NUMERIC, unit TEXT, condition TEXT,
  source TEXT, verified BOOLEAN DEFAULT FALSE, UNIQUE (grade, product_form, property));   -- numbers entered by a verifier, never by the spec
CREATE TABLE mtc_results (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id TEXT NOT NULL REFERENCES organizations(id),
  document_id UUID REFERENCES documents(id), cert_id UUID REFERENCES cert_records(id), lot_id UUID REFERENCES stock_lots(id),
  heat_no TEXT, grade_claimed TEXT, chemistry JSONB DEFAULT '{}', mechanical JSONB DEFAULT '{}',
  ce_iiw NUMERIC(5,3), pren NUMERIC(5,1), heat_treatment TEXT, ndt JSONB DEFAULT '[]', flags TEXT[] DEFAULT '{}',
  conformance TEXT CHECK (conformance IN ('CONFORMS','FAILS','INCOMPLETE','UNVERIFIED_REFERENCE','REQUIRES_REVIEW')),
  reference_verified BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT now());
```

### 9.3 Row-level security and disclosure
- RLS by `org_id` (session setting `app.current_org`, fail-safe: no setting means no rows) on `raw_items`, `documents`, `doc_lines`, `procurement_lines`, `stock_lots`, `usage_events`, `life_alerts`, `forward_indents`, `transfer_orders`, `cert_records`, `mtc_results`.
- `golden_masters` readable by all authenticated users.
- Cross-organisation views expose only golden code, descriptor, quantity bucket (e.g. "10-50") and site city. Exact quantity, price, vendor and bank fields only after the owner accepts a transfer.
- Aggregates read from materialized views with minimum group sizes.

### 9.4 Tamper-evident audit log
Append-only `audit_log(seq, at, actor, action, entity, entity_id, before, after, rationale, prev_hash, this_hash)`. A BEFORE INSERT trigger takes `pg_advisory_xact_lock(727001)`, reads the last hash, and sets `this_hash = sha256(prev_hash || concat_ws('|', at, actor, action, entity, entity_id, before, after, rationale))`. Triggers raise on UPDATE, DELETE and TRUNCATE for every role including the app role. `audit.record()` is called in the same transaction as the state change. `audit.verify_chain()` returns the first broken `seq`. A daily script writes the signed head hash to an external path; without it say "tamper-evident against application users", not "tamper-proof". Maker/checker is enforced on `users.id`, and one login session cannot hold both roles on a task.

### 9.5 Auth
Hackathon-grade HS256 JWT (`sub`, `org_id`, `role`), clearly labelled; production would use OIDC. Demo-token script.

---

## 10. Document intake (Stage 0) [P1]

**Document types and profiles**

| Type | Typical fields | Gives you |
|---|---|---|
| PO_GRN | PO no, GRN no, lines, qty, UoM, price, received date | Structured lines, price, received date |
| INVOICE | vendor, GSTIN, invoice no and date, lines, amounts | Vendor, price, duplicate detection |
| MTC_CERTIFICATE | heat/batch no, grade, chemistry, mechanical results, heat treatment, NDT | Certificate record, derived CE and PREN, conformance (10.2) |
| DATASHEET_LABEL | technical text, batch no, manufacture and expiry dates | Technical attributes, lot dates |

**Flow.** Upload; compute file hash and `invoice_key` (vendor GSTIN, invoice number, invoice date); duplicates warn or block (S10); use the PDF text layer when present, OCR otherwise; layout and table parse; one `doc_line` per item with page, bounding box and OCR confidence; each line becomes a `raw_item` (`source_type = PROCUREMENT_DOC`) and runs through the normal pipeline. Low-confidence HARD attributes become None with `LOW_OCR_CONFIDENCE` (S5). Review tasks use kind `DOC_REVIEW`; the UI shows the page image beside the extracted fields with the bounding box highlighted.

**Pre-procurement check.** `POST /docs/precheck` takes a datasheet or spec and returns matching golden masters with verdicts, creating nothing except an audit entry. This is the strongest "prevent the duplicate at the start" flow.

**Three concepts, one catalogue.** Item definition (golden master), purchase event (procurement line), physical lot (stock lot with batch and dates). There is no second item database.

**Confidentiality.** Price, vendor and bank fields follow RLS and disclosure levels (9.3).

**Providers.** `OCRProvider` protocol: Fake (sidecar JSON for CI and demo replay), local OCR, optional vision-LLM (dev only; output still passes the cross-validator and the OCR-confidence rule).

**Synthetic documents.** A generator makes 20+ documents across the four types and at least four organisations as digital PDFs and as noisy images (rotation, blur, low contrast) with ground-truth JSON, including deliberate failures: `WCB` read as `WC8`, smudged batch number, missing expiry date, duplicate invoice, credit note. An accuracy script reports field-level accuracy per type and per attribute and accuracy by confidence bucket.

---

### 10.1 Capture channels and OCR pipeline detail [P1]

**Channels** (stored in `documents.capture_channel`)
- `UPLOAD`: PDF, PNG, JPG or TIFF, size limit from config (default 15 MB `[ASSUMPTION]`).
- `CAMERA`: mobile or desktop browser capture through `getUserMedia` over HTTPS. The image enters the same pipeline as a scan. Required for field staff photographing a certificate or label.
- `PASTE`: pasted text skips OCR. Lines carry the flag `PASTED_TEXT`, and HARD attributes still pass the cross-validator.

**Pipeline**
1. Hash the bytes, check duplicates (S10), classify each page as PO/invoice, MTC, or datasheet/label/drawing by keyword and layout rules; the user can override.
2. Per page: if a text layer exists, read it with PyMuPDF. Otherwise rasterize at 300 DPI, apply a median filter (size 3), deskew by searching a configured set of candidate angles for maximum row-projection variance, and apply autocontrast.
3. Recognition goes through `OCRProvider`: local primary engine (PaddleOCR is the candidate), local fallback engine (EasyOCR is the candidate), the Fake provider for CI and replay, and the optional vision-LLM provider (dev only). Fall back when the primary raises or its mean page confidence is below `OCR_FALLBACK_CONF` `[ASSUMPTION]`. If neither candidate installs on the chosen Python version, use Tesseract and record the decision in `docs/decisions.md` `[VERIFY installs]`.
4. Layout: group boxes by vertical overlap, sort rows by median position, associate cells of borderless tables by box geometry, and link line items to heat or batch numbers.
5. Store per line: page, bounding box, `ocr_engine`, `ocr_conf`, `raster_dpi`. Uploads are processed in memory; files are written only to `STORAGE_PATH` after hashing, never to temporary paths.
6. Low-confidence HARD attributes become `None` with `LOW_OCR_CONFIDENCE` (S5). The review screen shows the page image beside extracted fields with the box highlighted.

**Tests.** Table-driven tests on synthetic scans (rotation, blur, low contrast, stamps over text). Field accuracy is reported per engine, per document type and per confidence bucket.

### 10.2 MTC certificate engine [P1]

Material test certificates (EN 10204 type 3.1 style `[VERIFY naming and scope]`) become structured, checkable records. Output is stored in `mtc_results` and links to a `cert_records` row and, when a heat or batch number matches, to a lot.

**Extraction** (same rules as section 7: evidence span on every value, invalid or low-confidence values become `None` plus a flag, decimal commas handled, units normalized)
- Heat or batch number, claimed material grade and product form.
- Chemistry, up to 17 elements: C, Mn, Si, P, S, Cr, Ni, Mo, Cu, V, Nb, N, Al, W, Co, Ti, B. Values outside 0 to 100% or a total above 100% give a flag and `None`.
- Mechanical: yield (ReH or Rp0.2), tensile, elongation, hardness (HBW, HRC or HV), Charpy energy with test temperature.
- Heat treatment condition and NDT endorsements (presence only).
- Statutory endorsements (for example an IBR form, a flameproof approval, a mine-equipment approval) are recorded as `cert_records` with `verified = false` until a person verifies them `[VERIFY names and bodies]`. They follow S12.

**Derived values** (computed only when every input is present; a missing element is never treated as zero; the result is `None` plus `CE_INCOMPLETE` or `PREN_INCOMPLETE`)
```
CE_IIW = C + Mn/6 + (Cr + Mo + V)/5 + (Ni + Cu)/15
PREN   = Cr + 3.3*Mo + 16*N
```
Worked check (computed by script, not typed): C 0.21, Mn 0.88, Cr 0.08, Mo 0.02, V 0.01, Ni 0.05, Cu 0.12 gives CE_IIW = 0.390. Weldability bands and PREN service thresholds are shown as indicative labels with `[VERIFY]` and an editable table; they never gate anything.

**Conformance against a reference.** Reference limits live in `grade_reference` (9.2). The spec supplies the structure and the grade list, not the numbers: a verifier enters each limit from the standard's text and sets `verified = true`.

Starter grades to seed (all rows `verified = false` until checked): ASTM A105, A216 WCB, A350 LF2, A182 F316, A182 F51, A335 P11, A335 P22, API 5L X52 and X65 (PSL2), plus the boiler-tube grades of 18.4.3.

Per-property verdict: `PASS`, `FAIL`, `NOT_REPORTED`, `NO_REFERENCE`. Overall result:
- `CONFORMS` only if the reference row set is verified, every required property is reported, and every property passes.
- `UNVERIFIED_REFERENCE` if any reference row used is unverified.
- `FAILS`, `INCOMPLETE`, or `REQUIRES_REVIEW` otherwise.

**S15.** An MTC never yields `CONFORMS` against an unverified reference row, and `stock_lots.mtc_verified` is set only by `CONFORMS` plus a heat or batch number match. A person can mark a lot as verified manually through maker-checker, with a rationale in the audit log.

**Sour service and NACE checks** are checklist items only (hardness and nickel limits `[VERIFY]` from the standard), never an automatic pass.

**Endpoint.** `POST /docs/{id}/mtc` (15.1). **UI.** `ChemistryTable`, CE and PREN badges with the `INDICATIVE` label, conformance panel showing whether the reference is verified.

**Tests.** Table-driven synthetic certificates: decimal comma, missing molybdenum (CE incomplete), smudged phosphorus (`None` and review), grade claimed but no reference, unverified reference (never `CONFORMS`), heat number mismatch against the lot.

---

## 11. Life monitor (Stage 9) [P1]

**Bases.** `SHELF_LIFE_DAYS` (from manufacture), `USAGE_COUNT` (e.g. parts machined), `USAGE_HOURS`. Roadmap, no schema change needed: calendar-from-install, inspection interval. A lot may have several policies; remaining life is computed per basis and the earliest-ending basis wins ("6 months or 100 parts, whichever first").

**Policy resolution.** Spec YAML `life` blocks, then per-organisation overrides in `life_policies`. No resolvable policy: status UNKNOWN. All limit values are `[ASSUMPTION]` or `[VERIFY]` until sourced from datasheets. Do not claim that pressure-rated pipes or similar items expire by calendar date; whether an item class carries calendar life or inspection-based life is an open `[VERIFY]`.

**Computation (pure functions, injectable `Clock`; never call `datetime.now()` in domain logic)**
- `remaining_life(lot, policy, usage, now)` per basis.
- `projected_depletion(events, window, min_events)`: fewer than the minimum gives INSUFFICIENT_DATA.
- `risk(lot, now, lead_times)`: GREEN, AMBER, RED, EXPIRED, UNKNOWN. Lead times per item class, `[ASSUMPTION]`, sized with the disposal process in mind.

**Alerts.** A nightly job creates alerts for store, site engineer and procurement manager, de-duplicated by `dedupe_key`, escalating after a configurable number of unacknowledged days.

**Disposition recommendation (ordered ladder; recommend and export only)**
1. Issue oldest first (FEFO).
2. Redeploy to a plant or CPSE that can consume it in time (separate near-expiry path).
3. Vendor retest, return or buy-back.
4. Official disposal request (export file). Disposal and auction rules for CPSEs: `[VERIFY]`.

**Sector life classes (all values `[VERIFY]` from datasheets; none is assumed):** refractory monolithics, mortars and gunning mixes (shelf life from manufacture); OTR tyres (expiry from the sidewall date code, per manufacturer storage guidance); elastomer and battery items as in the earlier classes. Fired refractory shapes, transformers, breakers, boiler tubes, pumps and belts carry no calendar life in this spec; whether any of them should is an open `[VERIFY]`. Wire ropes use discard criteria and inspection intervals, which are roadmap, not shelf life. `expiry_required: true` in the spec triggers S6.

**Integration.**
- Stream A: `is_stream_a_eligible(lot, now)` is False for expired lots and unknown expiry on classes that require it (S6). Near-expiry stock has its own redeployment path with its own recipients, so it does not conflict with the Stream A shelf-life ratio `[ASSUMPTION: 60%]`.
- Stream B: `max_poolable_quantity(item, consumption_rate, shelf_life)` caps pooled quantity so it can be consumed before expiry.

**Usage data.** Manual entry, CSV import or API in the first release; a simulator for the demo, stated plainly. Automatic capture from machine counters or an EAM is roadmap.

---

## 12. Standards, verification and ERP interoperability

**Standards catalogue** (reference IDs only, no standard text; everything `verified = false` until checked): process valves (API 600, API 602, API 6D, API 623, ASME B16.34, API 607); utility valves (IS 778, IS 14846 waterworks sluice valves, IS 13095; not hydrocarbon service `[VERIFY scope]`); process piping (ASTM A106 Gr B, A333 Gr 6, API 5L, ASME B36.10M; STD equals SCH 40 only up to 10" NB `[VERIFY]`); utility pipes (IS 1239 Part 1, IS 3589); flanges (ASME B16.5, B16.47 A/B, IS 6392); structural (IS 2062:2011, IS 808); rebar (IS 1786:2008); cables (IS 7098, IEC 60502-1, IEC 60332-3 or IS 10810; IS 1554 is PVC cable `[VERIFY]`); motors (IS 12615, IEC 60034-30-1, IEC 60079 series, IS 325); bearings (ISO 15, ISO 281, IS 5669 / IS 10324 `[VERIFY]`); fasteners (ASTM A193 B7/B7M, A194 2H/2HM, ASME B1.1, IS 1367, NACE MR0175 / ISO 15156); instrumentation (IEC 60079, IEC 61508/61511, IS 3624).

**Supersession seed rows (verify before use):** BS 5351 to ISO 17292 (partial); BS 1873 to API 623 (partial); IS 2062 older Fe 410 WA/WB/WC to E250 A/BR/B0 (partial; check chemistry, impact test, thickness limits `[VERIFY]`); IS 1239:1990 to 2004 (superseded; check tables); IS 14846 to API 600 (not equivalent).

**Statutory checks modelled as flags and checklists, not conclusions:** PESO/CCoE for Ex equipment, BIS CRS / QCO applicability, IBR for boiler tubes and steam piping, mine-equipment approvals for Group I electrical equipment and for mine winding ropes, fire-resistance approval for coal-mine belting, electricity-sector technical requirements for power equipment, Make in India orders. All `[VERIFY]`, including the names of the approving bodies.

**Sector standards (reference IDs only, `verified = false` until checked; full list in 18.4 to 18.7):** transformers (IS 2026 series, IS 1180, IEC 60076 series); switchgear (IEC 62271-100, IS 13118, IEC 60947-2); boiler tubes (ASME SA-213, SA-210, SA-192); refractories (Indian refractory standards, ISO 10081, ASTM C27); conveyor belts (Indian belting standards, DIN 22102, ISO 340); OTR tyres (ETRTO, TRA, ISO earth-mover designation); wire ropes (IS 2266, ISO 2408, API 9A); pumps (API 610 / ISO 13709, API 682 / ISO 21049, ISO 2858); hoses (SAE J517 classes, EN 853, EN 856, EN 857). Do not seed any equivalence between SAE and EN hose classes, or between ASME `SA` and ASTM `A` grades, as anything stronger than PARTIAL_EQUIVALENT with conditions.

**ERP.** Samanvay does not overwrite host ERP numbering; it produces a cross-reference and classification feed. The opaque code goes in an old-material-number or customer field, the descriptor is truncated by rule to the target field length, attributes go as classification rows. UNSPSC and GeM category IDs are exported when `verified`. **Field lengths are per-target, per-organisation configuration with `[VERIFY]` markers; never hard-coded.** Exports: CSV and XLSX for `sap`, `oracle`, `maximo` targets. Write-back (IDoc MATMAS, S/4 product API, MDG) is roadmap; always proposal mode. There is no "BAPI webhook".

**Verification register:** `docs/verification.md` with columns claim, source, verified by, date, status. Seed it with every `[VERIFY]` here and in code. A check fails the build if a `# VERIFY:` marker in code has no row.

---

## 13. Procurement streams, legal framing, value model [P2]

**Say:** CPSEs follow their own procurement manuals, DPE directives, CVC guidelines and GeM usage rules where applicable; the platform supports those processes and asserts no legal approval. Joint procurement needs an inter-CPSE MoU and delegations, with one CPSE as lead buyer `[VERIFY guidance]`. The tender pack is a structured export (XLSX, CSV, JSON) for officials; do not claim a GeM API integration. GFR 2017 is cited only as analogous practice `[VERIFY]`.

**Tender pack:** canonical title and parametric specification, total quantity in canonical UoM, consignee table, technical compliance checklist (BIS/QCO, PESO, IBR, NACE; all `[VERIFY]`), vendor-neutral spec text by default, PAC/justification field for proprietary items, Make-in-India declaration checklist (`[VERIFY]` thresholds and orders). The system never computes local-content percentages.

**Stream A mechanics (workflow states, not legal advice):** requirement match, technical acceptance (MTC, PMI for alloys, shelf-life ratio from config), commercial basis (book value, last purchase price or agreed; `[VERIFY inter-PSU guidance]`), tax invoice type (`[VERIFY]` with finance), dispatch. **Redeployability screen:** surplus only if no consumption in a configured window, criticality allows it, and quantity exceeds max stock or reorder need; no consumption data means "unknown" and excluded from savings.

**Value model (all inputs `[ASSUMPTION]`, low/base/high, editable):**
```
Stream A: avoided_purchase_cost = qty * recipient_current_price
          transfer_cost = qty * transfer_price + logistics + inspection
          net_benefit_A = avoided_purchase_cost - transfer_cost
Stream B: net_benefit_B = pooled_baseline_cost * discount_scenario(q) - pooling_admin_cost
```
Carrying-cost saving counts only for stock actually consumed or sold (`carrying_rate` `[ASSUMPTION]`). Procurement-document prices may replace assumed prices only where a `procurement_line` exists, with the source of every price labelled. Outage exposure is shown as exposure, never as savings. Pool only Tier 1 or steward-approved items. A requirement served by Stream A leaves the Stream B pool.

### 13.1 Pooling classes, discount scenarios, carrying cost (all `[ASSUMPTION]`)

Each subcategory declares `pooling_class` (BULK_MT, BULK_M, ENGINEERED). The discount table, low/base/high multipliers and the worked clusters are in section 19; every value is an editable assumption without a source, and the UI shows the range. Carrying cost is shown as a stated breakdown (cost of capital, storage and preservation, insurance and handling, obsolescence), each part editable, and it counts only for stock actually consumed or sold. A 20% annual total (9.5, 4.0, 1.5 and 5.0 across those four parts) is the placeholder default, to be replaced by CPSE finance figures. Inter-organisation transfers carry a tax-treatment checklist item (inter-state or intra-state invoice type) to be settled with finance `[VERIFY]`; the spec does not state the tax outcome. Outage exposure is displayed as exposure, never as savings.

---

### 13.2 Surplus and spare locator [P2]

A map and table that answers "who else holds this item, how far away, and is it usable?" It uses PostgreSQL only; a graph database is not needed for a distance and filter query.

- **Locations.** Each organisation's `profile.plants[]` carries `{code, city, lat, lon}`. Distance is the great-circle distance computed in SQL. Road distance and freight are roadmap.
- **Filters.** Golden master or descriptor search, maximum distance, minimum idle days (configurable `[ASSUMPTION]`), quantity bucket, risk status. Only lots that pass S6 and S12 appear (not expired, expiry known where required, statutory certificate present) and only for Tier 1 or steward-approved masters.
- **Disclosure.** Other organisations see golden code, descriptor, quantity bucket and city only. Exact quantity, price, vendor and contact appear after the owner accepts a request (9.3).
- **Map.** Tiles need internet. In offline demo mode the screen renders a plain scatter of plants with city labels and the same filters.
- **Action.** "Request transfer" creates a Stream A requisition draft (13), never a transaction.

---

## 14. Evaluation (measured, not asserted)

**Datasets.** Public/seed (GeM catalogue items, public tender BoQs, public material requisitions from any CPSE), synthetic (noise generator: token reorder, abbreviation, dropped attributes, unit swaps HP/kW and inch/NB and kg/cm2/bar, typos, Indic transliterations, separator changes), steward-labelled (200+ pairs by domain engineers from more than one organisation if possible). Every pair carries provenance and the organisations involved. Split 60/20/20 by group; never tune on test.

**Buckets.** (1) Dialect positives; (2) noisy positives; (3) adversarial hard negatives differing in exactly one critical attribute (Class 150/300, 6312/6313, 4C x 16 / 4C x 25, 4C / 3.5C, ISMB 300 / 350, ISMB / ISLB 300, WCB / WC6, B7 / B7M, 2-pole / 4-pole, Ex d / Ex e, IIB / IIC as identity, CS / SS body, SCH 40 / 80, E250A / E250BR); (4) missing-attribute cases (expected Tier 2); (5) injected extraction errors; (6) proprietary/OEM cases; (7) document-intake cases (OCR noise on HARD attributes); (8) life-status cases against a hand-labelled lot table; (9) sector packs: hard negatives per family (15+ per deep family, 8+ per standard family, listed in section 18) and identity-mode cases (OEM part number, drawing revision, Ex Group I vs II, statutory attribute missing); (10) MTC cases (decimal comma, missing elements, smudged digits, unverified reference).

**Metrics.** Pairwise precision/recall/F1; false-merge rate on hard negatives with a Clopper-Pearson 95% upper bound (0 of 150 observed is a bound of about 2.4%, say that); tier distribution and steward tasks per 1,000 items; per-attribute extraction accuracy per domain; missing-attribute routing (must be 100%); MTC field accuracy and conformance routing (never `CONFORMS` against an unverified reference: 100%); extraction-error leakage; LOW_OCR_CONFIDENCE routing; document field accuracy; life-status correctness; latency p50/p95 (SQL-only and end-to-end separately); scale test at 100k items (500k if possible).

**Organisation parity.** Every headline metric is also reported per organisation; flag any organisation deviating from the overall value by more than a configured margin. **Sector parity:** every headline metric is also reported per sector pack, with the same deviation flag; a sector with fewer than 100 test pairs is shown with its interval and labelled low-sample.

**Baselines side by side.** (a) cosine-only on raw text, (b) trigram-only on raw text, (c) Samanvay rule-based path; (d) Samanvay with the optional ML layer (8.1), reported separately and only when enabled. The measured cosine score for a Class 150 vs Class 300 pair is computed by a script, never hard-coded.

**Gate (`make eval-gate`) fails if** hard-negative false merges > 0, missing-attribute routing < 100%, a LOW_OCR_CONFIDENCE item reaches Tier 1, an MTC conforms against an unverified reference, or auto-tier precision on dev is below target. The report states the provenance mix, that synthetic data was generated by the team, and the limitations.

---

## 15. Interface, API, layout

**Screens (priority order)** 1 Standardizer [P0]; 2 Diff inspector (green EXACT, amber MISSING/UPGRADE, red MISMATCH; hover shows evidence; copy says "explains the decision") [P0]; 3 Stewardship queue (filters, bulk approve of identical-signature clusters, maker-checker states, keyboard shortcuts, server-side pagination) [P0]; 4 Document intake (upload, extracted lines beside page image with bounding boxes and OCR-confidence colouring, DOC_REVIEW flow, duplicate warning, pre-procurement check) [P1]; 5 Lots and alerts (risk table, remaining life per basis, usage chart, acknowledge, disposition panel, disposal-request export, visible banner when clock or usage is simulated) [P1]; 6 Upload and mapping with ingest report; 7 Health card (score and breakdown per 20.1); 8 Golden catalogue with lifecycle actions, aliases, where-used; 9 Pooling and tender pack; surplus match and transfer [P2]; 10 CFO dashboard [P2]; 11 Audit and metrics (chain verification, evaluation incl. per-organisation and per-sector parity); 12 OEM onboarding wizard [P1] (20.2). Navigation has a sector filter; sector packs are listed from `GET /packs`. Requirements: role-aware navigation, organisation switcher with no default organisation, server-side tables, empty/error/loading states, accessible components, "demo mode" banner. Hindi UI strings via i18n files [P2].

**Merged-edition additions.** 13 Home dashboard [P1] (15.2). Document intake gains camera capture and paste text (10.1). An MTC panel with `ChemistryTable`, CE and PREN badges and conformance state sits in the document screen (10.2). 14 Spare locator [P2] (13.2). The diff inspector may show a separate, labelled "Model score attribution" panel when the ML layer is on (8.1(d)); the attribute diff always remains the explanation of the decision.

**API**
```
POST /ingest/jobs   GET /ingest/jobs/{id}         POST /match
POST /docs          GET /docs/{id}  GET /docs/{id}/lines   POST /docs/precheck   POST /docs/{id}/mtc   GET /metrics   GET /locator
GET /tasks          POST /tasks/{id}/propose|approve|reject
POST /golden        PATCH /golden/{id}   POST /golden/{id}/merge|split   GET /golden/{id}  GET /golden/search
GET /lots  GET /lots/{id}  POST /lots/{id}/usage  POST /usage/import  GET /lots/{id}/disposition
GET /alerts  POST /alerts/{id}/ack
POST /pools  POST /pools/{id}/export   GET /availability   POST /transfers  PATCH /transfers/{id}/gate
GET /value?scenario=   GET /erp/export?target=&format=
GET /metrics/eval  GET /metrics/health  GET /metrics/catalog-health  GET /metrics/workload  GET /audit  GET /audit/verify
GET /packs   POST /oem/onboard   POST /oem/onboard/{id}/propose|approve   POST /drawings/equivalence
```
Every state change writes `audit_log` in the same transaction. Every route has an auth dependency or an explicit allow-list entry (tested).

**Layout**
```
samanvay/
  docker-compose.yml .env.example Makefile pyproject.toml alembic.ini AGENTS.md
  db/{init,migrations,seed}/   packs/{common,power,steel,mining,heavy_eng}/{specs,lexicons,parsers,fixtures,eval,standards,demo}   dictionaries/{abbreviations.yaml,indic/<lang>.yaml,bearing_suffix_xref.yaml,section_properties.csv}
  orgs/ (optional per-org config)
  api/{main.py,config.py,database.py,logging_setup.py,routers/,models/,schemas/,security/,
       services/{normalize,uom,codes,audit,rls,classify,candidates,compare,tiering,scoring,canonical,embeddings,
                 ingest,lifecycle,steward,docs,ocr,mtc,taxonomy,life,pool,transfer,locator,value,erp,metrics,jobs}.py,
       extractors/{base.py,registry.py,size.py,pressure.py,cable.py,motor.py,structural.py,lexicons/*.yaml},
       ml/{subvectors,ner,rerankers,explain}.py}   # optional layer (8.1), off by default
  worker/ eval/ scripts/ web/ tests/ docs/
```

---

### 15.1 API contract examples

Examples are illustrative and use synthetic values. Evidence spans are character offsets into the raw description. The organisation comes from the JWT, never from the request body. Hashes are shown as `<sha256>` placeholders. Error bodies use a stable `code` field the UI can switch on.

**`POST /match`**: a description with several REQUIRED attributes missing is Tier 2, never auto-linked.
```json
// request
{ "description": "VLV GT 100 NB CL150 WCB FLG RF API600", "category_hint": null, "top_k": 3 }

// response 200
{
  "clean_text": "VALVE GATE 100 NB CL150 WCB FLG RF API600",
  "subcategory": "VALVES.GATE",
  "category_confidence": 0.97,
  "flags": [],
  "extracted": {
    "size_nb":         { "value": 100,        "confidence": 0.95, "evidence": [7, 13] },
    "pressure_class":  { "value": "ASME_150", "confidence": 0.95, "evidence": [14, 19] },
    "body_material":   { "value": "A216_WCB", "confidence": 0.95, "evidence": [20, 23] },
    "end_connection":  { "value": "FLANGED",  "confidence": 0.95, "evidence": [24, 27] },
    "facing":          { "value": "RF",       "confidence": 0.95, "evidence": [28, 30] },
    "design_standard": { "value": "API_600",  "confidence": 0.95, "evidence": [31, 37] }
  },
  "candidates": [
    {
      "golden_code": "MPNG-0004821937-3",
      "descriptor": "VALVES.GATE | 100NB | CL150 | A216-WCB | FLG-RF | API600",
      "tier": 2,
      "prob": 0.93,
      "reason_codes": ["MISSING_REQUIRED"],
      "verdicts": [
        { "attr": "size_nb",         "role": "HARD",     "raw": 100,        "golden": 100,        "verdict": "EXACT" },
        { "attr": "pressure_class",  "role": "HARD",     "raw": "ASME_150", "golden": "ASME_150", "verdict": "EXACT" },
        { "attr": "body_material",   "role": "HARD",     "raw": "A216_WCB", "golden": "A216_WCB", "verdict": "EXACT" },
        { "attr": "end_connection",  "role": "HARD",     "raw": "FLANGED",  "golden": "FLANGED",  "verdict": "EXACT" },
        { "attr": "facing",          "role": "HARD",     "raw": "RF",       "golden": "RF",       "verdict": "EXACT" },
        { "attr": "design_standard", "role": "HARD",     "raw": "API_600",  "golden": "API_600",  "verdict": "EXACT" },
        { "attr": "trim_code",       "role": "REQUIRED", "raw": null,        "golden": "API_TRIM_8", "verdict": "MISSING" },
        { "attr": "bonnet_type",     "role": "REQUIRED", "raw": null,        "golden": "BOLTED",   "verdict": "MISSING" },
        { "attr": "operator",        "role": "REQUIRED", "raw": null,        "golden": "HANDWHEEL", "verdict": "MISSING" },
        { "attr": "fire_safe",       "role": "REQUIRED", "raw": null,        "golden": "API_607",  "verdict": "MISSING" },
        { "attr": "sour_service",    "role": "REQUIRED", "raw": null,        "golden": "NO",       "verdict": "MISSING" }
      ],
      "attribute_gap_alert": "Missing: trim_code, bonnet_type, operator, fire_safe, sour_service"
    }
  ]
}
```

**`POST /tasks/{id}/approve`**: maker-checker and domain-tag enforcement.
```json
// request
{ "rationale": "Datasheet page 2 confirms trim and fire-safe design." }

// 200
{ "task_id": 482, "state": "APPROVED", "decided_by": "<user uuid>", "audit_seq": 10924, "audit_hash": "<sha256>" }

// 403 (same user proposed and approves)
{ "code": "MAKER_CHECKER_VIOLATION", "message": "The approver must differ from the proposer." }

// 403 (safety-critical subcategory, checker lacks the segment tag)
{ "code": "DOMAIN_TAG_REQUIRED", "required": ["COMMON"], "message": "Approval needs the domain tag of this subcategory." }
```

**`GET /docs/{id}/lines`**
```json
{
  "document_id": "<uuid>", "status": "IN_REVIEW", "capture_channel": "CAMERA",
  "lines": [
    { "line_id": "<uuid>", "page": 1, "bbox": [0.08, 0.31, 0.84, 0.34],
      "raw_text": "GATE VALVE 4 INCH 150# A216 WCB FLANGED RF API 600",
      "ocr_engine": "paddleocr", "raster_dpi": 300, "ocr_conf": 0.982,
      "fields": { "qty": 4, "uom": "EA", "batch_no": null, "expiry_date": null },
      "flags": [] }
  ]
}
```

**`POST /docs/{id}/mtc`**
```json
{
  "document_id": "<uuid>", "heat_no": "HT-94810-A", "grade_claimed": "A105",
  "chemistry": { "C": 0.21, "Mn": 0.88, "Si": 0.22, "P": 0.015, "S": 0.012, "Cr": 0.08, "Ni": 0.05, "Mo": 0.02, "Cu": 0.12, "V": 0.01 },
  "mechanical": { "yield_mpa": 285, "tensile_mpa": 530, "elongation_pct": 28.5, "hardness": { "scale": "HBW", "value": 156 },
                  "charpy": { "energy_j": 48, "temp_c": -20 } },
  "ce_iiw": 0.390, "ce_label": "INDICATIVE", "pren": null, "flags": ["PREN_INCOMPLETE"],
  "heat_treatment": "NORMALIZED", "ndt": ["UT"],
  "conformance": "UNVERIFIED_REFERENCE", "reference_verified": false,
  "requires_review": true
}
```

**`GET /lots?risk=AMBER`**: Stream A eligibility follows S6 and the shelf-life ratio, and the response says why.
```json
{
  "as_of": "2026-10-10", "clock": "REAL",
  "lots": [
    { "lot_id": "<uuid>", "golden_code": "<MPNG code>", "descriptor": "STEEL.REFRACTORY | CASTABLE | ...",
      "batch_no": "B-2026-04", "mfg_date": "2026-04-01", "expiry_date": "2027-04-01",
      "remaining_days": 173, "risk": "AMBER", "basis": "SHELF_LIFE_DAYS",
      "qty_remaining": 15.0, "uom": "MT",
      "stream_a_eligible": false, "reason": "SHELF_LIFE_RATIO_BELOW_THRESHOLD", "near_expiry_path": true }
  ]
}
```
(173 days of a 365-day life is a ratio of about 47%, below the 60% `[ASSUMPTION]`, so the lot goes to the near-expiry path and not Stream A.)

**`GET /audit/verify`**
```json
{ "verified_records": 10924, "first_broken_seq": null, "head_hash": "<sha256>", "anchored_head": "<sha256 or null>", "status": "OK" }
```

### 15.2 Observability and dashboard [P1]

**Metrics.** `GET /metrics` in Prometheus format, behind the allow-list with network restriction (tested). Labels carry sector, tier, document type and engine, never organisation, item or user identifiers, so metrics cannot leak between CPSEs and cardinality stays bounded.

| Type | Series |
|---|---|
| Counter | `samanvay_match_total{sector,tier}`, `samanvay_docs_ingested_total{doc_type,status}`, `samanvay_steward_actions_total{action,domain}`, `samanvay_audit_entries_total`, `samanvay_mtc_results_total{conformance}`, `samanvay_ocr_fallback_total{from,to}` |
| Histogram | `samanvay_match_seconds{stage}`, `samanvay_ocr_page_seconds{engine}`, `samanvay_reranker_seconds{sector}` (only when the ML layer is on) |
| Gauge | `samanvay_review_queue_depth{domain}`, `samanvay_life_red_lots`, `samanvay_jobs_queued`, `samanvay_audit_chain_ok` |

**Dashboard screen.** A home view for the signed-in organisation: review queue depth by domain, tier distribution, harmonization progress (codes before and after), duplicate rate, OCR engine readiness, last audit verification result, and the catalog health score. Counts come from the same materialized views as the health card, with the minimum group sizes of 9.3.

---

## 16. Testing and definition of done

**Testing.** Table-driven unit tests per extractor (deep domains 40+ strings, standard domains 20+, each including the failure cases above); Hypothesis property tests for S1 to S10 (at least 300 to 500 examples, deadline disabled, never skipped, plus a mutation check that deliberately breaks Tier 1 gating and confirms the tests fail); golden-file comparator tests (full verdict matrix); audit tests (update/delete blocked, concurrent inserts keep a valid chain, tamper detected); RLS tests across three organisations; role-matrix API tests; evaluation run in CI on the locked test set.

**Definition of done**
- All 21 families have a spec, extractor tests and measured accuracy (depth stated: 6 deep, 15 standard); anything cut is listed as spec-only on the limitations slide.
- Each of the five packs meets the pack definition of done (18.1); removing any one pack leaves the core and the others passing.
- Hard-negative bucket: 0 Tier 1 merges observed, bound reported; missing-attribute bucket: 100% Tier 2.
- Cold start works on a 100k-row synthetic file; dedup report generated.
- Maker-checker, lifecycle, audit verification, RLS and neutrality tests pass.
- Document intake, the MTC engine and the life monitor work end to end on synthetic data; the full-chain demo runs.
- No MTC reaches `CONFORMS` against an unverified reference (S15); `/metrics` exposes the series in 15.2; the home dashboard renders from the same views as the health card.
- The optional ML layer is either shown to pass its gate (8.1) or left off and listed on the limitations slide.
- Every `[VERIFY]` is resolved, removed or listed as open on a limitations slide; `[ASSUMPTION]` values show ranges in the UI.
- `make demo` works on a clean machine offline after one-time downloads; a replay mode covers live OCR or model failure.

---

## 17. Pitch (8 minutes) and jury Q&A

**Pitch.** (0:00-0:45) same valve, three descriptions, three codes. (0:45-2:00) upload a messy file from one organisation: "N codes collapse to M masters". (2:00-3:30) safety moment: cosine-only merges Class 150 with Class 300 (show the measured score), Samanvay refuses, diff inspector shows red; a missing-attribute item goes to review. (3:30-5:00) full chain: upload a scanned GRN, a label and an MTC (a smudged value becomes None and goes to review; carbon equivalent is computed only from complete data), low-confidence field routed to review, corrected, matched to an existing master from another organisation, lot created, simulated clock moves it AMBER then RED, alert, disposition recommendation. (5:00-6:00) evaluation: baselines, false-merge bound, workload, per-organisation parity. (6:00-7:00) stewardship, audit verification, governance (central vs federated, disclosure levels), value dashboard and tender pack if built. (7:00-8:00) honest limits and a pilot plan (one plant of one participating CPSE, one domain, 4 weeks, read-only ERP extracts).

**Sector beat (add to the 2:00-3:30 safety moment):** show one hard negative from each new sector, for example transformer `DYN11` vs `DYN1`, belt FRAS vs non-FRAS, and a Group I vs Group II motor, each refused with the diff inspector in red.

**Words to avoid:** "zero false merge", "statutory pricing formula", "meets statutory requirements", "auto-conforms", "100% explainable", "mathematically tamper-proof", "GFR compliant", "GeM API integrated", "sells surplus", "sub-10ms" or any latency not measured and reported, "mandated" or "legally binding" for any rule not in the verification register, any savings figure not labelled as a scenario.

**Jury Q&A (short answers)**
1. *Why not SAP MDG or commercial MDM?* Strong inside one enterprise; ours is cross-CPSE federation with disclosure controls, Indian standards and statutory flags, steward-first safety gating, on-prem option. We would integrate, not replace.
2. *Accuracy?* Locked test set, baselines, confidence intervals, tier workload, injected-error scenario, per-organisation parity, provenance labelled.
3. *Missing or wrong attributes?* Tier 2; rule and LLM must agree on HARD attributes; low-confidence OCR is treated as missing.
4. *Why upload documents?* It captures attributes at purchase time and checks for an existing master before a new code is requested.
5. *Is life tracking an EAM?* No: lot-level shelf and usage life with recommendations; machine counters and EAM integration are roadmap.
6. *Can you sell expiring stock?* The platform recommends and exports a request; disposal follows each CPSE's rules.
7. *Confidentiality between CPSEs?* RLS, disclosure levels, no prices before transfer acceptance, federated mode roadmap.
8. *Vigilance?* Append-only hash-chained audit with external anchoring, maker-checker bound to identities.
9. *Financial impact?* Scenario model with explicit assumptions; Stream A and B separate; exposure never counted as savings.
10. *Languages?* Per-language dictionaries plus a multilingual encoder; Indic accuracy reported separately.
11. *Does it only work for refineries?* No. The core is segment-agnostic; power, steel, mining and heavy engineering are built as domain packs with their own specs, parsers, fixtures and evaluation, and we report accuracy per sector. Families we have not built are listed as roadmap.
12. *Who approves a joint tender across separate CPSEs?* Each CPSE follows its own delegations and procurement manual; joint procurement needs an inter-CPSE MoU with one CPSE as lead buyer `[VERIFY guidance]`. The platform produces the pooled specification and consignee table; it asserts no legal approval.
13. *Make in India local content?* Local content is product and supplier specific, so the platform computes no percentages. It produces a declaration checklist for officials `[VERIFY orders and thresholds]`.
14. *A proprietary part we have never seen?* It resolves through OEM part number or alias; otherwise it becomes a DRAFT proprietary master in the steward queue, and the onboarding wizard handles catalogue-scale loads. Text similarity alone never links an OEM or drawing-keyed item (S14).
15. *Why PostgreSQL with pgvector, not a vector database?* One datastore means one backup, one security model and transactional consistency with the audit log. We report measured p50 and p95 latency at 100k items, not a promised figure.
16. *How do you handle units of measure?* Controlled vocabulary, conversion from tables and formulas, original and canonical quantities stored; a conversion that needs an unknown attribute raises a flag instead of guessing (for example brick weight, or head vs pressure for pumps).
17. *Coal-mine electrical equipment?* Group I (mines) and Group II (surface) are different regimes; the system never treats them as equal or substitutable (S11), and approval numbers are statutory attributes that block Tier 1 when missing (S12) `[VERIFY approving bodies]`.
18. *Boiler tubes and IBR?* Tubes are matched on OD, wall, wall basis, grade and manufacturing route; the IBR certificate is a per-lot record, and a lot without it is never issued or transferred `[VERIFY]`.
19. *Can you really cover 21 families in four weeks?* Six are deep and fifteen standard, all YAML-driven, with measured accuracy per family and a published cut order; anything cut is shown as spec-only rather than claimed.
20. *How do you add a new sector?* Add a pack folder (spec, lexicon, parsers, fixtures, evaluation pairs, standards seeds) and run `make test-pack`; no change to the core.
21. *Why not a vector database or a graph database?* One PostgreSQL gives one backup, one security model and audit written in the same transaction; pgvector reports measured latency at 100k items, and a distance filter does not need a graph.
22. *Do you validate certificates?* We extract chemistry and mechanical values, compute carbon equivalent and PREN only from complete data, and compare against reference limits that a person has verified. Until a reference row is verified, the result says so and nothing is marked conforming (S15).
23. *What does the ML layer add?* Recall on messy text and a ranking score, measured against the rule-based path. It cannot raise a tier, and it ships only if it passes the evaluation gate.

---

## 18. Sector domain packs (Power, Steel, Mining, Heavy engineering)

The problem statement names Oil & Gas, Power, Steel, Mining and Heavy Engineering. Each sector is a **domain pack**: one folder holding everything the sector needs, so a pack can be built, tested, demoed or cut on its own.

**Standards in this section are reference IDs only.** Every standard number, statutory body, rating convention and life value below is `[VERIFY]` until a row exists in `docs/verification.md`. Nothing here is a claim of compliance, and no standard text is reproduced.

### 18.1 Pack structure and pack definition of done

```
packs/<pack>/{specs/*.yaml, lexicons/*.yaml, parsers/*.py, fixtures/*.csv, eval/pairs.csv, standards/seed.csv, demo/cluster.csv, README.md}
packs: common | power | steel | mining | heavy_eng
```

The core loads every `packs/*/`. Where earlier sections say `specs/` or `extractors/lexicons/`, read `packs/<pack>/specs/` and `packs/<pack>/lexicons/`.

**A family is "done" when:** the spec YAML validates; the lexicon and parsers pass table-driven tests (including the failure cases listed below); fixtures meet the depth count (deep 40+, standard 20+); hard-negative pairs meet the count (deep 15+, standard 8+); extraction accuracy is measured per attribute and reported; and one synthetic demo cluster exists. `make test-pack PACK=power` runs one pack. A CI test removes each pack in turn and confirms the core and the other packs still pass (principle 1.3.7).

**New spec keys** (loaded and validated like the rest of the registry):

```yaml
identity_mode: PARAMETRIC | OEM_PN | DRAWING     # section 5.3
safety_critical: true                            # checker needs the domain tag (4.7)
pooling_class: BULK_MT | BULK_M | ENGINEERED     # section 13.1
expiry_required: true                            # S6 applies: unknown expiry is never GREEN
attributes:
  - {name: ..., role: HARD, statutory: true}     # S12
```

### 18.2 Pack index (21 families: 6 deep, 15 standard)

| Pack | Family | Depth | Identity mode | Safety-critical | Statutory attribute | Life class |
|---|---|---|---|---|---|---|
| common | Valves | deep | PARAMETRIC | yes | | |
| common | Motors (with Ex Group I/II) | deep | PARAMETRIC | yes | Ex approval | |
| common | Pipes, Flanges, Cables, Structural, Rebar, Bearings, Fasteners, Instrumentation | standard | PARAMETRIC | yes (pressure and Ex items) | Ex approval (instruments) | |
| power | Power and distribution transformers | deep | PARAMETRIC | yes | | |
| power | HT/LT circuit breakers | standard | PARAMETRIC | yes | | |
| power | Boiler tubes | standard | PARAMETRIC | yes | IBR certificate | |
| steel | Refractories | deep | PARAMETRIC (brand grades via OEM_PN) | no | | monolithics: shelf life |
| steel + mining | Conveyor belts | standard | PARAMETRIC | yes (FRAS) | | |
| steel | Mill rolls | standard | DRAWING | no | | |
| mining | Off-the-road (OTR) tyres | deep | PARAMETRIC (brand SKUs via OEM_PN) | no | | ageing: expiry from date code |
| mining + steel + heavy_eng | Wire ropes | standard | PARAMETRIC | yes | mine-winding approval | |
| heavy_eng | Centrifugal pumps (complete) and pump spares | deep | PARAMETRIC / OEM_PN | yes | | |
| heavy_eng | Hydraulic hoses | standard | PARAMETRIC | yes | | |
| heavy_eng | Made-to-drawing parts (castings, forgings, fabrications) | standard | DRAWING | no | | |

Families shared by several sectors carry a segment list, for example `segment: [STEEL, MINING]`. They are built once.

### 18.3 Cross-sector token collisions (extend the 4.2 table)

| Token | Collides with | Rule |
|---|---|---|
| `ROLL` | conveyor idler roller, paper roll, bearing roller | `MILL_ROLL` only with WORK, BACKUP, INTERMEDIATE or PINCH plus a barrel dimension |
| `BELT` | V-belt, safety belt | conveyor belt only with a carcass code (EP, ST, NN) or ply count plus width |
| `ST` | steel cord belt, structural steel, stainless | `ST` + strength number inside a belt context only |
| `EP` | epoxy | `EP` + `NNN/N` or `EP NNN` inside a belt context only |
| `T22`, `T91`, `T11` | Ex temperature class `T1`-`T6` | the T-class parser requires a single digit and a word boundary; boiler-tube grades are parsed only in `BOILER_TUBE` (test: `SA213 T22` yields no t_class) |
| `TUBE` | boiler tube, pipe, tyre inner tube, instrument tubing | decided by classification, never by the word alone |
| `I` | Roman numeral, "item" | Ex Group I parsed only inside an `EX` token sequence |
| `R` | radial (tyre), rating, reducer | radial only in the tyre size pattern |
| `FC` | fibre core (rope), flow control | rope core only in `WIRE_ROPE` |

### 18.4 POWER pack

#### 18.4.1 Transformers (deep) `POWER.TRANSFORMER`

```yaml
subcategory: POWER.TRANSFORMER
segment: [POWER]
identity_mode: PARAMETRIC
safety_critical: true
pooling_class: ENGINEERED
primary_dimension: {attr: rating_kva, unit: KVA}
attributes:
  - {name: rating_kva,        role: HARD}          # ONAN (base) rating
  - {name: phases,            role: HARD}
  - {name: hv_kv,             role: HARD}
  - {name: lv_kv,             role: HARD}
  - {name: frequency_hz,      role: HARD}
  - {name: vector_group,      role: HARD}
  - {name: cooling,           role: HARD}
  - {name: insulation_medium, role: HARD}
  - {name: tap_changer,       role: HARD}          # ON_LOAD | OFF_CIRCUIT
  - {name: design_standard,   role: HARD}
  - {name: rating_kva_max,    role: REQUIRED}      # extended cooling stage, e.g. ONAF
  - {name: tap_range,         role: REQUIRED}
  - {name: impedance_pct,     role: REQUIRED}
  - {name: bil_kv,            role: REQUIRED}
  - {name: winding_material,  role: REQUIRED}
  - {name: installation,      role: REQUIRED}      # OUTDOOR | INDOOR
  - {name: manufacturer,      role: SOFT}
```

**Parsers (Python where logic is real, the rest in the lexicon):**
- Rating: canonical kVA; `MVA` x 1000. Dual ratings `20/25 MVA` give `rating_kva = 20000` and `rating_kva_max = 25000`, matched to cooling `ONAN/ONAF`. A single number with dual cooling gives flag `RATING_STAGE_UNKNOWN`.
- Voltage pair: `33/11KV`, `132/33 KV`, `11/0.433KV`, `11KV/415V`, `11/.433`. Never read `11/0.433` as a fraction. Normalize to kV with the HV side first. A pair with HV < LV gets `VOLTAGE_ORDER_SWAPPED` and is not auto-corrected.
- Vector group: after the normalizer uppercases, match `(?<![A-Z0-9])(YN|Y|D|ZN|Z)(YN|Y|D|ZN|Z)(0|1|5|6|7|11)(?![A-Z0-9])` and canonicalize to `Dyn11` form (HV capital, LV lowercase, clock number). Other clock numbers parse with flag `VECTOR_GROUP_UNUSUAL`. Required tests: `DYN11`, `DYN-11`, `YNyn0`, `YND1`; `DYNAMIC` yields nothing.
- Cooling: `ONAN`, `ONAF`, `OFAF`, `ODAF`, `AN`, `AF`; dual forms `ONAN/ONAF` kept as an ordered list.
- Tap changer: `OLTC`, `ON LOAD` give ON_LOAD; `OCTC`, `OFF CIRCUIT`, `NLTC`, `NO LOAD` give OFF_CIRCUIT. Range: `+5% TO -15% IN 16 STEPS`, `+/-10% IN 2.5% STEPS` give a structured `{plus, minus, step_pct, steps}`.
- Insulation medium: MINERAL_OIL, SYNTHETIC_ESTER, NATURAL_ESTER, SILICONE, DRY_CAST_RESIN.
- Impedance `7.15%` is REQUIRED. Parallel-operation tolerance is `[VERIFY]` against the transformer standard.

**Substitution (never identity).** A higher kVA offered for a lower requirement is `UPGRADE`: substitution only, with engineering sign-off (footprint, impedance, fault level, protection settings). Parallel operation needs the same voltage ratio, vector group, and compatible impedance `[VERIFY]`.

**Hard negatives (15+):** `DYN11` vs `DYN1`; 33/11 vs 33/6.6 kV; ONAN vs ONAF as the only rating basis; on-load vs off-circuit tap changer; mineral oil vs dry type; Cu vs Al winding (REQUIRED mismatch gives Tier 3 unless overridden); indoor vs outdoor; 1.6 vs 2 MVA; 11/0.433 vs 11/0.415 kV (flagged as a nominal-voltage question, Tier 2); missing vector group (Tier 2).

**Descriptor:** `POWER.TRANSFORMER | 10000KVA | 33/11KV | DYN11 | ONAN | ON_LOAD | MINERAL_OIL | <standard>`. Insulating oil is a separate consumable item and is not part of the transformer master.

**Reference IDs (verified=false):** IS 2026 series, IS 1180 (distribution), IEC 60076 series `[VERIFY]`.

#### 18.4.2 Circuit breakers (standard) `POWER.BREAKER`

| HARD | REQUIRED |
|---|---|
| breaker type (VCB, SF6, ACB, MCCB, MCB), rated voltage kV, rated current A, rated short-circuit breaking current kA, short-time duration s, poles, frequency, mounting (fixed or withdrawable), design standard | operating mechanism, auxiliary and control voltage, number of aux contacts, protection release type |

Parse `25KA/3S`, `31.5 KA 3 SEC`, `1250A`, `33KV`, `3P`/`4P`. A higher kA at the same voltage and mounting is a substitution `UPGRADE` only (panel fit and coordination need engineering sign-off). Hard negatives: 25 vs 31.5 kA; 1 s vs 3 s; VCB vs SF6; fixed vs withdrawable; 1250 vs 1600 A; 3P vs 4P. Reference IDs `[VERIFY]`: IEC 62271-100, IS 13118, IEC 60947-2.

#### 18.4.3 Boiler tubes (standard) `POWER.BOILER_TUBE`

| HARD | REQUIRED |
|---|---|
| OD mm, wall mm, wall basis (MINIMUM or NOMINAL), material specification, grade (T11, T22, T91, T92, A1, C), manufacturing route (seamless hot-finished or cold-drawn) | spec body (ASME `SA` or ASTM), length type, supplementary NDT, heat-treatment condition, `ibr_cert` (statutory, per lot) |

Boiler tubes use OD and wall, never NB. The size parser must not run here (add to the test list: `60.3 OD X 5.6 WT` in BOILER_TUBE returns no NB). `MWT` and `NWT` give the wall basis; an unstated basis gives `WALL_BASIS_UNKNOWN` and Tier 2. `SA213 T22` and `ASTM A213 T22` differ in `spec_body` (REQUIRED): Tier 2, not Tier 3 `[VERIFY]`. Hard negatives: T22 vs T91; A213 vs A210; min vs nominal wall; seamless vs ERW; 51 vs 54 mm OD. The IBR certificate is attached per lot in `cert_records` (9.2); a lot without it is never issued or transferred (S12). Reference IDs `[VERIFY]`: ASME SA-213, SA-210, SA-192; the Indian Boilers Regulations.

### 18.5 STEEL pack

#### 18.5.1 Refractories (deep) `STEEL.REFRACTORY`

```yaml
subcategory: STEEL.REFRACTORY
segment: [STEEL]
identity_mode: PARAMETRIC
safety_critical: false
pooling_class: BULK_MT
expiry_required: true        # applies to monolithics, mortars, gunning and ramming mixes; not to fired shapes
attributes:
  - {name: form,            role: HARD}   # BRICK | CASTABLE | RAMMING_MASS | GUNNING_MIX | MORTAR | FIBRE | PRECAST_SHAPE
  - {name: material_class,  role: HARD}   # FIRECLAY | HIGH_ALUMINA | MAGNESIA | MAG_CARBON | MAG_CHROME | ALUMINA_CARBON | SILICA ...
  - {name: key_chemistry,   role: HARD}   # e.g. {AL2O3_MIN_PCT: 70} or {MGO_MIN_PCT: 97, C_PCT: 14}
  - {name: shape_code,      role: HARD, when: "form in [BRICK, PRECAST_SHAPE]"}
  - {name: dimensions_mm,   role: HARD, when: "form in [BRICK, PRECAST_SHAPE]"}   # L x W x T, taper as T1/T2
  - {name: cement_class,    role: HARD, when: "form == CASTABLE"}                 # CONVENTIONAL | LOW_CEMENT | ULTRA_LOW | CEMENT_FREE
  - {name: bond,            role: REQUIRED}                                       # RESIN | PITCH | CERAMIC | CHEMICAL | HYDRAULIC
  - {name: max_service_c,   role: REQUIRED}
  - {name: bulk_density,    role: REQUIRED}
  - {name: brand_grade,     role: SOFT}      # brand grades take the OEM_PN path when a manufacturer part number is present
life:
  - {basis: SHELF_LIFE_DAYS, value: null, source: "datasheet (mandatory)"}   # VERIFY per product; unknown = UNKNOWN, never GREEN
```

**Parsers.** Chemistry: `AL2O3 70% MIN`, `70 % AL2O3`, `MGO-C 10`, `C 14%`, `MGO 97`. Dimensions: `230X114X75`, `230 X 114 X 75/65` (taper). Shape: `STRAIGHT`, `ARCH`, `WEDGE`, numbered shape codes kept as given, not interpreted. Quantity: MT-to-EA conversion for shaped bricks needs `piece_weight_kg` or `bulk_density` plus dimensions; otherwise `MissingConversionAttribute`, never a guess. A manufacturer grade name alone does not determine chemistry; chemistry is taken from the datasheet attribute or stays `None`.

**Hard negatives (15+):** Al2O3 70 vs 80%; MgO-C 10 vs 14% carbon; 230x114x75 vs 230x114x65; straight vs arch; resin vs pitch bond; low-cement vs conventional castable; castable vs ramming mass; fireclay vs high-alumina at the same dimensions; missing chemistry (Tier 2).

**Life.** Monolithic products carry a shelf life from manufacture `[VERIFY per datasheet]`; the demo lot table includes one expired and one unknown-expiry castable lot (S6).

**Descriptor:** `STEEL.REFRACTORY | BRICK | MAG_CARBON | MGO_MIN_97 | C14 | 230X114X75 | STRAIGHT | RESIN`. Reference IDs `[VERIFY]`: the Indian refractory standards and ISO 10081 / ASTM C27 classification.

#### 18.5.2 Conveyor belts (standard, shared with MINING) `STEEL.CONVEYOR_BELT`

| HARD | REQUIRED |
|---|---|
| carcass type (EP, NN, ST, solid-woven PVC), strength class (e.g. EP 630, ST 1600 N/mm), ply count (fabric), belt width mm, fire-resistance class (NONE, FR, FRAS) | cover thickness top+bottom mm, cover grade, splice type, roll length m |

Parse `EP 630/4 1200MM 6+3`, `ST 1600 1400 MM 10+6 FRAS`, `1200 MM 4 PLY EP 400/4`. In `EP 630/4`, 630 is the strength class and 4 the plies; a ply count that disagrees with the strength-class suffix gives `PLY_CONFLICT`. FRAS vs non-FRAS is HARD and safety-critical (underground use). Hard negatives: EP630/4 vs EP630/3; 1200 vs 1400 mm; FRAS vs non-FRAS; 6+3 vs 8+3 cover; ST1600 vs ST2000. Reference IDs `[VERIFY]`: the Indian belting standards, DIN 22102, ISO 340 (flammability), and the coal-mine belting approval regime.

#### 18.5.3 Mill rolls (standard) `STEEL.MILL_ROLL`

`identity_mode: DRAWING`. HARD: roll type (WORK, BACKUP, INTERMEDIATE, PINCH), material (forged steel, SG iron, HSS, adamite), barrel diameter mm, barrel length mm, drawing number (normalized, with owner). REQUIRED: neck dimensions, hardness range, drawing revision, mill and stand reference (goes to aliases). A re-ground roll is a different condition: `item_condition = REGROUND` with `remaining_diameter_mm`; Stream A offers it only with that attribute present. Hard negatives: barrel 600 vs 650 mm; same barrel, different neck; same drawing number from different owners; revision A vs B.

### 18.6 MINING pack

#### 18.6.1 OTR tyres (deep) `MINING.OTR_TYRE`

```yaml
subcategory: MINING.OTR_TYRE
segment: [MINING]
identity_mode: PARAMETRIC
safety_critical: false
pooling_class: ENGINEERED
expiry_required: true        # expiry derived from the tyre date code (manufacture week and year)
attributes:
  - {name: section_width,   role: HARD}   # 27.00, 33.00, 40.00, or 59/80 style
  - {name: aspect_ratio,    role: HARD, when: "section_width has aspect"}
  - {name: construction,    role: HARD}   # RADIAL | BIAS
  - {name: rim_diameter_in, role: HARD}
  - {name: tread_code,      role: HARD}   # e.g. E3, E4, L4, L5
  - {name: star_rating,     role: REQUIRED}   # VERIFY meaning per manufacturer
  - {name: tube_type,       role: REQUIRED}   # TUBELESS | TUBE_TYPE
  - {name: ply_or_casing,   role: SOFT}
  - {name: manufacturer,    role: SOFT}
life:
  - {basis: SHELF_LIFE_DAYS, value: null, source: "manufacturer storage guidance (mandatory)"}   # VERIFY
```

**Parser.** `(?P<w>\d{2}(?:\.\d{1,2})?(?:/\d{2})?)\s*(?P<c>R|-)\s*(?P<rim>\d{2})`, run only in the `OTR_TYRE` family. `27.00R49`, `27.00-49`, `33.00 R 51`, `59/80R63`, `18.00-25`, `23.5R25`. `R` gives RADIAL; `-` gives BIAS. The same size with R and with `-` are different items (HARD). Date code: week and year from the sidewall or label; an unreadable code gives `LOW_OCR_CONFIDENCE` or `None`, and expiry is UNKNOWN.

**Hard negatives (15+):** 27.00R49 vs 27.00R51; E3 vs E4; radial vs bias at the same size; 33.00R51 vs 33.00R49; tubeless vs tube-type; 1 star vs 2 star; missing tread code (Tier 2).

**Descriptor:** `MINING.OTR_TYRE | 27.00 | R | 49 | E4 | TUBELESS`. Manufacturer SKUs are aliases and take the OEM_PN path. Reference IDs `[VERIFY]`: ETRTO and TRA size conventions, ISO earth-mover tyre designation.

#### 18.6.2 Wire ropes (standard, shared with STEEL and HEAVY_ENG) `MINING.WIRE_ROPE`

| HARD | REQUIRED |
|---|---|
| diameter mm, construction (`6X36 WS`, `6X19 S`, `8X19 S`, `6X41 SFW`), core (FC, IWRC), lay (RHOL, LHOL, RHLL, LHLL), tensile grade N/mm2 (e.g. 1570, 1770, 1960), surface finish (BRIGHT, GALVANIZED) | preformed, lubrication, length m, termination, approval or test certificate (statutory for mine winding ropes) |

Parse `6X36 WS IWRC 26MM 1770`, `26 MM DIA 6X36WS+IWRC RHOL`, `6X19+FC`. A higher grade or larger diameter is never a default substitute (design factor); substitution needs engineering sign-off. Hard negatives: 6x36 vs 6x19; FC vs IWRC; RHOL vs LHOL; 26 vs 28 mm; 1770 vs 1960; bright vs galvanized. Reference IDs `[VERIFY]`: IS 2266, ISO 2408, API 9A, and the mine-ropes approval regime.

#### 18.6.3 Ex Group I extension (applies to motors, instrumentation, switchgear)

Coal-mine equipment is certified for methane-prone mines under **Group I**, a different regime from surface industries (**Group II**, gas groups IIA/IIB/IIC with T-classes).

- Add attributes: `ex_groups` (set of `I`, `II`), `epl` (Group I: Ma, Mb, Mc; Group II: Ga, Gb, Gc), `statutory_approval_no` (statutory, S12) `[VERIFY the approving bodies]`.
- Parser: `Ex d I`, `EX D I (MB)`, `Ex d IIB T4 Gb`, dual marking `Ex d I/IIB`. For Group I, `gas_group` and `t_class` are `None` by definition and are **not** counted as missing.
- Identity compares `ex_groups` as sets. Group I and Group II are different regimes: never equal and never substitutes (S11). The IIC >= IIB >= IIA lattice applies within Group II only. Dual-certified equipment against a single-group requirement is Tier 2 with both certificates shown.
- Hard negatives: `Ex d I` vs `Ex d IIA T4`; `Ex d I` vs `Ex e I`; missing approval number (Tier 2).

### 18.7 HEAVY_ENG pack

#### 18.7.1 Centrifugal pumps (deep) `HEAVY.PUMP_CENTRIFUGAL`

Two identity modes in one family. **Complete pumps** are PARAMETRIC. **Pump spares** (impeller, shaft, wear ring, casing, bearing housing, mechanical seal) are OEM_PN keyed to a parent pump model, so text similarity alone never gives Tier 1 (S14).

```yaml
subcategory: HEAVY.PUMP_CENTRIFUGAL
segment: [HEAVY_ENG, COMMON]
identity_mode: PARAMETRIC          # spares are classified to HEAVY.PUMP_SPARE with identity_mode OEM_PN
safety_critical: true
pooling_class: ENGINEERED
primary_dimension: {attr: flow_m3h, unit: M3H}
attributes:
  - {name: pump_type,        role: HARD}   # API: OH1 OH2 OH3 OH4 OH5 OH6 BB1 BB2 BB3 BB4 BB5 VS1-VS7 | ISO2858 | OTHER
  - {name: flow_m3h,         role: HARD}   # rated
  - {name: head_m,           role: HARD}   # rated, liquid column
  - {name: speed_rpm,        role: HARD}
  - {name: suction_nb,       role: HARD}
  - {name: discharge_nb,     role: HARD}
  - {name: flange_class,     role: HARD}   # ASME_CLASS or PN, same rules as 7.2
  - {name: material_class,   role: HARD}   # API S-6, C-6, A-8 ... or explicit casing/impeller grades
  - {name: seal_arrangement, role: HARD}   # SINGLE | DOUBLE | TANDEM
  - {name: design_standard,  role: HARD}
  - {name: impeller_dia_mm,  role: REQUIRED}
  - {name: driver_kw,        role: REQUIRED}
  - {name: seal_plan,        role: REQUIRED}
  - {name: npshr_m,          role: SOFT}
  - {name: manufacturer,     role: SOFT}
```

**Parsers.** Flow to m3/h from a table: `1 L/S = 3.6`, `1 LPM = 0.06`, `1 US GPM = 0.2271247`, `1 IMP GPM` kept as a separate unit with a table value. Head to metres: `FT x 0.3048`. **Never convert head to pressure or the reverse** (needs density): `KG/CM2` on a pump line gives flag `PRESSURE_NOT_HEAD`. Nozzle pair `4X3-10` is a manufacturer-family designation (suction x discharge x nominal impeller, inches) and parses to suction 100 NB, discharge 80 NB, nominal impeller 10 in with flag `OEM_SIZE_CODE` `[VERIFY the convention per manufacturer]`. Speed from `2950 RPM` or poles through the 50 Hz table, with slip noted: 2950 and 3000 map to the same two-pole class but are different rated speeds, so `speed_rpm` is compared with a configured tolerance and anything outside it is a MISMATCH. Required tests: `100 M3/HR @ 50 M HEAD`, `440 GPM`, `25 L/S`, `4X3-10`, `API 610 OH2`.

**Hard negatives (15+):** OH2 vs BB2; S-6 vs C-6; single vs double seal; 2950 vs 1450 rpm; 100 vs 120 m3/h; suction 100 vs 125; A-8 vs S-6; impeller 250 vs 270 mm (REQUIRED mismatch, Tier 3 unless overridden); duty point stated without units (Tier 2).

**Descriptor:** `HEAVY.PUMP_CENTRIFUGAL | OH2 | 100M3H | 50M | 2950RPM | 100X80NB | CL300 | S-6 | DOUBLE-SEAL`. Reference IDs `[VERIFY]`: API 610 / ISO 13709, API 682 / ISO 21049, ISO 2858.

**Spares (`HEAVY.PUMP_SPARE`).** Identity key: normalized (OEM, part number). `parent_equipment_model` and `equipment_tag` go to aliases and where-used. A description with only "IMPELLER FOR PUMP 4X3-10" and no part number or drawing is Tier 2 at best, with a draft master offered.

#### 18.7.2 Hydraulic hoses (standard) `HEAVY.HYDRAULIC_HOSE`

| HARD | REQUIRED |
|---|---|
| standard class (SAE 100R1AT, R2AT, R12, R13, R15; EN 853 1SN/2SN; EN 856 4SP/4SH; EN 857 1SC/2SC), inner size (dash size or DN mm) | end fittings (JIC 37 degree, BSP, NPT, ORFS, flange code), assembly length, stated working pressure |

Parse dash `-8`, `DN12`, `1/2"`. SAE and EN classes are different systems and are never equal at identity level; a steward-maintained `standard_relations` row (PARTIAL_EQUIVALENT with conditions `[VERIFY]`) makes the pair Tier 2 instead of Tier 3. A stated working pressure that conflicts with the standard class and size gives `PRESSURE_CONFLICT`. Hard negatives: R1AT vs R2AT; -8 vs -10; 1SN vs 2SN; JIC vs BSP.

#### 18.7.3 Made-to-drawing parts (standard) `HEAVY.MADE_TO_DRAWING`

`identity_mode: DRAWING`, for castings, forgings and fabrications bought to a drawing.

| HARD | REQUIRED |
|---|---|
| normalized drawing number, drawing owner (OEM or in-house), material specification and grade | revision, heat treatment, item name, approximate weight kg (SOFT with tolerance) |

Normalization: uppercase, collapse spaces and hyphens inside the number, keep sheet and item suffixes (`D-44120` and `D44120` are the same; `D44120-1` and `D44120-2` are not). The key includes the drawing owner, because numbers collide across OEMs. Revision: same normalized drawing and same revision allows Tier 1; a different revision is always Tier 2 with both shown. A steward can approve a `drawing_revision_equivalence` row (maker-checker, with engineering rationale); after that the pair can be Tier 1 (S13). Hard negatives: same drawing, rev A vs B; same item name, different drawing; same drawing number, different owner; different material grade.

### 18.8 Roadmap families (document only, do not build, no invented standards)

Transmission conductors (ACSR/AAAC named conductors; map names to IS designations from a verified table only) `[VERIFY]`; insulators; instrument transformers; protection relays; coal-mill and fan spares; turbine spares (OEM_PN); explosives and detonators (statutory handling; out of scope) `[VERIFY]`; rail and wagon items; gearboxes; mining drill consumables and ground-engaging tools (OEM_PN heavy).

### 18.9 UoM notes for the new families

Transformers, breakers, pumps, tyres: `EA`. Refractory bricks and monolithics: `MT` base; `EA` for shaped bricks needs `piece_weight_kg`. Conveyor belts and wire ropes: `M` base; a roll or reel is `ROLL` or `DRUM` with a stated length. Hoses: `EA` for assemblies, `M` for bulk hose. Boiler tubes: `M` or `EA` by stated length; weight per metre uses the 7.6 pipe formula only when OD and wall are both known. A conversion needing an unknown attribute raises `MissingConversionAttribute`.

---

## 19. Demo seed clusters (script-generated)

Fourteen synthetic clusters: ten across the common pack and one per new sector. **Every number below was computed by script from the inputs; the real seed must be produced by `scripts/seed_clusters.py`, never typed.** All data is synthetic. Use neutral organisation labels (for example `OIL-1`, `POWER-2`, `STEEL-1`, `MINE-1`, `HEAVY-1`), or put a "synthetic data" banner on any screen that shows real organisation names; never attribute invented quantities or prices to real organisations.

**Rules the clusters demonstrate**
- The discount class follows the unit of the pooled quantity: BULK_MT for tonnes, BULK_M for metres, ENGINEERED for counted units (a stud-bolt set is a counted unit).
- Only Tier 1 or steward-approved items enter a pool, and a unit counts in Stream A or Stream B, never both.
- Cluster 1 (motors) shows the gate at work: of the raw items, one is Tier 1, two are Tier 2 and one is Tier 3 (legacy efficiency class). The compliant pool is 4 units (8 after steward approval), below the 10-unit threshold, so scenario savings are 0. This is deliberate: safety gating can reduce claimed savings, and the number is honest.

### 19.1 Discount scenario table (all values `[ASSUMPTION]`, editable, unsourced)

| Class | Quantity bands | Table discount |
|---|---|---|
| BULK_MT | <25 MT; 25-99; 100-299; 300-499; >=500 | 0%; 8%; 12%; 15%; 18% |
| BULK_M | <1,000 m; 1,000-4,999; 5,000-9,999; 10,000-19,999; >=20,000 | 0%; 8%; 12%; 15%; 18% |
| ENGINEERED (counted units) | <10; 10-24; 25-49; 50-99; >=100 | 0%; 8%; 12%; 15%; 18% |

These values are unsourced defaults. The UI shows low (0.5x), base (1x) and high (1.25x, capped at 25%). **For the pitch, quote the low scenario**, and show the table as an editable assumption.

### 19.2 Computed clusters (INR)

| # | Item | Pooled qty | Independent cost (INR) | Class | Table % | Low (0.5x) | Base (1x) | High (1.25x, cap 25%) | Note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Motors 55 kW 4P B3 Ex d IIB T4 IE3 | 4 EA | 1,920,000 | ENG | 0% | 0 | 0 | 0 | Tier 1 only (O1). Tier 2 items need steward approval; Tier 3 item excluded |
| 1b | same, after steward approves both Tier 2 items | 8 EA | 3,940,000 | ENG | 0% | 0 | 0 | 0 | the legacy-efficiency (EFF3) item stays excluded (Tier 3) |
| 2 | ISMB 300 E250A, 12 m | 360 MT | 23,269,000 | BULK_MT | 15% | 1,745,175 | 3,490,350 | 4,362,938 |  |
| 3 | TMT 25 mm Fe 500D | 550 MT | 32,169,000 | BULK_MT | 18% | 2,895,210 | 5,790,420 | 7,238,025 |  |
| 4 | Cable 1.1 kV 4C x 16 Cu SWA XLPE FRLS | 15,500 M | 6,556,500 | BULK_M | 15% | 491,738 | 983,475 | 1,229,344 |  |
| 5 | Bearing 6312-2Z-C3 | 310 EA | 1,209,850 | ENG | 18% | 108,886 | 217,773 | 272,216 |  |
| 6 | Gate valve 150 NB Cl300 WCB RF | 69 EA | 3,653,700 | ENG | 15% | 274,028 | 548,055 | 685,069 |  |
| 7 | Pipe 100 NB SCH 80 A106 Gr B | 4,800 M | 15,424,000 | BULK_M | 8% | 616,960 | 1,233,920 | 1,542,400 | |
| 8 | Stud bolt set M24 x 150 B7/2H | 8,500 EA | 2,374,000 | ENG | 18% | 213,660 | 427,320 | 534,150 | counted units use the engineered table |
| 9 | Pressure transmitter 0-10 bar HART SS316L Ex d IIC T6 | 45 EA | 3,714,000 | ENG | 12% | 222,840 | 445,680 | 557,100 |  |
| 10 | WN flange 200 NB Cl150 RF A105 SCH STD | 140 EA | 2,042,000 | ENG | 18% | 183,780 | 367,560 | 459,450 |  |

**New-sector clusters (illustrative prices; replace with script-generated values within configured bands):**

| # | Item | Pooled qty | Independent cost (INR) | Class | Table % | Low (0.5x) | Base (1x) | High (1.25x, cap 25%) | Note |
|---|---|---|---|---|---|---|---|---|---|
| 11 | Distribution transformer 100 kVA 11/0.433 kV DYN11 ONAN, Cu | 125 EA | 31,255,000 | ENG | 18% | 2,812,950 | 5,625,900 | 7,032,375 | illustrative prices |
| 12 | MgO-C brick, 14% C, resin bond | 260 MT | 24,920,000 | BULK_MT | 12% | 1,495,200 | 2,990,400 | 3,738,000 | illustrative prices |
| 13 | OTR tyre 27.00R49 E4 | 52 EA | 78,200,000 | ENG | 15% | 5,865,000 | 11,730,000 | 14,662,500 | illustrative prices |
| 14 | Centrifugal pump API 610 OH2 (complete pump) | 15 EA | 27,100,000 | ENG | 8% | 1,084,000 | 2,168,000 | 2,710,000 | illustrative prices |

Safety moments to seed in each new cluster: (11) one record with the vector group missing (Tier 2) and one `DYN1` record (Tier 3); (12) one castable lot with unknown expiry (UNKNOWN, never GREEN, S6); (13) one record `27.00R51` (Tier 3) and one with no tread code (Tier 2); (14) one pump record with `KG/CM2` given as head (flag `PRESSURE_NOT_HEAD`, Tier 2).

---

## 20. Catalog health score and OEM onboarding wizard

### 20.1 Catalog health score

Shown on upload and again after harmonization, per organisation, per subcategory and per sector, so the before/after is visible.

```
item_completeness = sum(weight(a) for a in applicable attributes that are populated and unflagged)
                    / sum(weight(a) for a in applicable attributes)
weight: HARD = 2, REQUIRED = 1, SOFT = 0 (not scored)
applicable = attributes whose `when` condition holds for the item
catalog_completeness = mean(item_completeness) over classified items
```

Also report, separately and never blended into one number: classified share (items with a subcategory above the confidence floor), items in `CATEGORY_UNCERTAIN`, extraction-flag rate by flag, duplicate rate (item codes per master), and the top missing attributes per subcategory (for example "pole count missing on 28% of motor records"; the figure comes from the data, not from this spec). Items that could not be classified are listed, not scored as zero. Statutory attributes show as their own line.

### 20.2 OEM catalogue onboarding wizard [P1]

For proprietary and OEM-keyed families (pump spares, brand-grade refractories, tyre SKUs, OEM instrument parts).

1. A Maker uploads an OEM catalogue (CSV, XLSX or digital PDF).
2. The system extracts OEM, part number, drawing number, parent equipment model and description, and proposes DRAFT masters with `identity_mode = OEM_PN`, keyed on normalized (OEM, part number). Existing aliases are matched first; supersession rows (`oem_part_supersession`) are applied.
3. The Maker reviews proposals in bulk (accept, edit, reject) with the evidence span beside each row.
4. A Checker holding the domain tag approves (maker-checker, 4.7). Approval publishes the masters and writes aliases; sister organisations' raw items that carry the same key then link as Tier 1 on the next match run, and anything without an exact key stays Tier 2.
5. The eval script reports steward minutes per master and the share of proposals accepted without edits. **Do not quote a fixed approval time in the pitch**; quote the measured one.

---

## 21. Build protocol: phases, gates and prompt template

Each phase is one agent session. The agent starts with the prompt template below, works only on that phase, and stops at its gate. A phase is accepted only when every gate command passes and the listed outputs exist. If a gate fails twice, the agent writes the blocker to `docs/open-questions.md` and stops instead of changing the gate.

**Prompt template (paste into the CLI at the start of each phase)**
```
Read AGENTS.md and docs/PROGRESS.md. Then read SPEC section(s): <sections for this phase>.
Implement phase <N>: <name>. Deliverables: <list>. Gate: <commands>.
Follow the operating rules. Do not begin the next phase. At the end, update docs/PROGRESS.md
with what was built, what is open, and the exact gate output.
```

| Phase | Days | Spec sections | Deliverables | Gate |
|---|---|---|---|---|
| 1 Foundation | 1-2 | 3, 9, 22 | repo scaffold, Docker Compose (`db`, `api`, `worker`, `web` stub), migrations for the section 9.2 schema, audit log with triggers, RLS, identity codes with Verhoeff, JWT auth and demo-token script, organisation and user seeds (at least four organisations in four sectors) | `make check` green; `make db-reset` works from empty; audit tests (update, delete and truncate blocked; concurrent inserts keep a valid chain; tamper detected); RLS tests with four organisations; Verhoeff known-vector tests including single-digit and transposition errors; every route has an auth dependency or an allow-list entry (tested) |
| 2 Normalize and UoM | 3-4 | 4.1, 4.2, 7.6, 18.3, 18.9 | ingest parser with per-organisation mapping profiles, normalizer, per-language dictionaries, category-gated abbreviations, UoM tables and conversions | table-driven tests; Indic combining marks preserved; `MissingConversionAttribute` raised, never guessed; ingest idempotent on file hash; per-row error report |
| 3 Extractor core | 5-6 | 5, 5.3, 7, 18.1 | YAML lexicon engine, extractor base and registry with category gating, evidence spans, spec registry loader and validator, identity modes | registry loads every pack; invalid YAML is rejected with a clear error; invalid values become `None` plus a flag; size parser tests from 7.1 pass |
| 4 Comparator and safety | 7-8 | 4.6, 5.1, 5.2, 5.4, 6 | per-attribute verdicts (EXACT, MISSING, MISMATCH, UPGRADE), tiering, directional lattices, S1 to S15 property tests, mutation check | Hypothesis runs at least 300 examples per invariant, never skipped; the mutation test breaks Tier 1 gating on purpose and the suite fails; golden-file verdict matrix passes |
| 5 Deep families | 9-13 | 7.2-7.5, 18.4-18.7 | valves, motors with Ex I/II, transformers, refractories, OTR tyres, pumps: lexicons, parsers, 40+ fixtures and 15+ hard-negative pairs each | per family: accuracy report per attribute; 0 hard negatives reach Tier 1; missing-attribute cases are 100% Tier 2 |
| 6 Standard families | 14-16 | 7, 18 | the other 15 families (the `common` pack first), 20+ fixtures and 8+ hard negatives each | same checks as phase 5; `make test-pack PACK=<each>`; removing any one pack leaves the others passing |
| 7 Match and ingest | 17-19 | 4.4, 4.5, 8 | classification, embeddings behind `EmbeddingProvider`, candidate generation, scoring (rule-based first), `/match`, ingest jobs, cold start with dedup report, golden lifecycle | cold start runs on a 100,000-row synthetic file; dedup report generated; p50 and p95 latency recorded (SQL-only and end-to-end separately) |
| 8 Stewardship and eval | 20-21 | 4.7, 8, 14 | tasks API with maker-checker and domain-tag rule, feedback, metrics, evaluation harness, baselines, `make eval-gate` | eval gate passes; three baselines reported side by side; per-organisation and per-sector parity reported |
| 9 Frontend core | 22-23 | 15 | standardizer, diff inspector, stewardship queue, role-aware navigation, organisation switcher with no default, demo banner | Playwright tests for the three screens; empty, error and loading states exist; server-side pagination |
| 10 Intake and life | 24-25 | 10, 10.1, 10.2, 11 | OCR provider protocol with fake, local and optional vision providers, document intake with duplicate detection and OCR pipeline detail, MTC engine with `grade_reference`, pre-procurement check, life monitor with injectable clock, alerts, disposition ladder | S5, S6, S7, S8, S10 and S15 tests pass; MTC table-driven tests pass; synthetic document generator and accuracy script run; life-status tests against the hand-labelled lot table |
| 11 Polish | 26-27 | 15, 19, 20 | document and lot screens, dashboard, camera capture, MTC panel, health card, OEM onboarding wizard, Prometheus metrics, demo seed scripts, hardening | `make demo` works on a clean machine offline; replay mode covers OCR or model failure; every `[VERIFY]` marker in code has a register row; `/metrics` exposes the 15.2 series |
| 12 Finish | 28 | 16, 17 | docs, limitations slide, rehearsal; streams, tender pack, value model, ERP export, locator and the optional ML layer only if ahead | definition of done in section 16 |

---

## 22. Repository bootstrap

### 22.1 First steps (no versions are pinned here)
1. `git init`; create the layout in section 15; add `.gitignore`, `.env.example`, `README.md`, `AGENTS.md`.
2. `uv init`; add the backend dependencies listed in section 3 with `uv add`; commit `uv.lock`.
3. Check that the `pgvector/pgvector` image tag for the chosen PostgreSQL major version exists before writing it into `docker-compose.yml`.
4. Create `web/` with the Next.js starter using `pnpm`; add the frontend libraries listed in section 3; check the Node version Next requires.
5. Record every resolved version in `docs/VERSIONS.md`.
6. Create empty `docs/verification.md`, `docs/PROGRESS.md`, `docs/decisions.md`, `docs/open-questions.md`, `docs/limitations.md`.

### 22.2 Makefile targets
`setup`, `up`, `down`, `db-reset`, `migrate`, `seed`, `test`, `test-pack PACK=<name>`, `lint`, `typecheck`, `check` (lint, typecheck, test), `eval`, `eval-gate`, `demo`, `verify-claims` (fails if a `# VERIFY:` marker in code has no register row), `audit-verify`, `loadtest`, `test-mtc`, `test-ml` (only when `ML_LAYER=on`).

### 22.3 `AGENTS.md` (contents)
```
# Samanvay agent rules
- Source of truth: SPEC.md in this repo. Work one phase at a time (section 21). Stop at the gate.
- Never invent external facts (standards, statutory rules, field lengths, versions). Mark [VERIFY] and add a row to docs/verification.md.
- Resolve versions with uv and pnpm; record in docs/VERSIONS.md. Never pin from memory.
- Tests first for the comparator and safety invariants. Never skip, loosen or delete a property test.
- Safety invariants S1 to S15 are never relaxed. Conflicts go to docs/open-questions.md.
- Data over code: new families and attribute values are YAML edits.
- Every state change writes audit in the same transaction.
- Run `make check` before each commit; commit small.
- Long session: update docs/PROGRESS.md and continue from it.
- Commands: see Makefile. Stack and layout: SPEC sections 3 and 15.
```

### 22.4 `.env.example` (variables)
`DATABASE_URL`, `JWT_SECRET`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `OCR_PROVIDER` (fake, local, vision), `LLM_EXTRACTOR` (off, local, hosted), `LLM_BASE_URL`, `TAU_AUTO`, `TAU_REVIEW`, `OCR_CONF_MIN`, `CLOCK_MODE` (real, simulated), `DEMO_MODE`, `ERP_TARGET`, `STORAGE_PATH`, `ML_LAYER` (off, on), `OCR_FALLBACK_CONF`, `METRICS_ENABLED`, `UPLOAD_MAX_MB`.

### 22.5 Docker Compose
Services `db` (PostgreSQL with the extensions in 9.2), `api`, `worker` (same codebase, job loop), `web`. Volumes for the database and document storage. Everything runs offline after one-time image and model downloads.
