# Samanvay (One Nation, One Material Code)

AI-Driven Standardization and Harmonization of Material Codes Across Central Public Sector Enterprises (CPSEs).

---

## 1. Project Purpose

Central Public Sector Enterprises (such as ONGC, IOCL, NTPC, SAIL, and Coal India) purchase millions of materials. Each enterprise assigns its own custom material code, description, and classification.
Because codes differ, enterprises cannot easily identify identical materials, pool their demand, or redeploy surplus stock.

**Samanvay** solves this problem:
- It harmonizes material descriptions into a single, permanent National Material Code (`MPNG-` prefix with a Verhoeff check digit).
- It never merges safety-critical items on text similarity alone.
- It shows engineers an exact, explainable diff showing why two items match or do not match.
- It tracks the life of items (shelf life and usage cycles) to prevent waste and hazardous degradation.

---

## 2. Core Documentation Links

This repository uses a structured documentation and plan framework:

- [specsheet.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/specsheet.md): The master technical specification and single source of truth.
- [implementation_plan.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/implementation_plan.md): The module-driven, spec-driven, and skill-driven master build plan (Modules 0 through 11).
- [implemented_till_now.md](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/implemented_till_now.md): The live implementation status tracker, changes log, and multi-session continuity protocol.
- [.agents/skills/](file:///C:/Users/mayank/Developement/Projects/SamanvayAI/.agents/skills): The collection of specialized engineering skills used by coding agents to build every module.

---

## 3. Architecture Overview

```
 Browser (Next.js): Standardizer, Diff Inspector, Stewardship Queue, Documents, Life Monitor
        |
        v  REST / JSON (FastAPI)
 +-----------------------------------------------------------------------------------------+
 | INGEST       | Parse CSV/XLSX, store raw payload, detect script, normalize text        |
 | EXTRACT      | TOML lexicons + Python parsers -> typed attributes + evidence spans     |
 | CLASSIFY     | Category rules + embedding fallback -> candidate blocks                 |
 | RETRIEVE     | Exact aliases, OEM part numbers, block_key, pg_trgm fuzzy recall        |
 | COMPARE      | Deterministic attribute diff (EXACT, MISSING, MISMATCH, UPGRADE)        |
 | TIER         | Tier 1 (Auto), Tier 2 (Review), Tier 3 (Distinct) -> S1 to S15 safety   |
 | STEWARD      | Maker-Checker workflow, domain tag access, feedback learning            |
 | DOCUMENT     | Multi-channel intake, OCR pipeline, MTC chemistry & mechanical engine   |
 | LIFE MONITOR | Shelf life, usage counter, risk ladder (GREEN, AMBER, RED, EXPIRED)     |
 +-----------------------------------------------------------------------------------------+
        |
        v
 PostgreSQL 18: pgvector, pg_trgm, pgcrypto, Row-Level Security, SHA-256 Audit Chain
```

---

## 4. Theory & Technical Principles (Simplified Technical English)

### 4.1 Identity Is Not Substitution
Two materials are identical only when all physical and standard parameters match.
- A **Class 300** valve cannot safely replace a **Class 150** valve without dimensional engineering review.
- High similarity score (e.g. 0.96 cosine) between Class 150 and Class 300 must **never** cause an auto-merge.
- Higher specification items are marked `UPGRADE` (substitution candidate only, requiring human sign-off). They are never given the same national code.

### 4.2 Opaque National Code (Verhoeff Algorithm)
National material codes use the format: `MPNG-` + 10 digits + `-` + 1 Verhoeff check digit (total 17 characters).
- Example: `MPNG-0004821937-3`.
- The Verhoeff check digit uses the dihedral group $D_5$ to detect:
  - 100% of single-digit errors (for example: typing `4` instead of `5`).
  - 100% of adjacent transposition errors (for example: typing `82` instead of `28`).
- The code is opaque and permanent: merging or reclassifying a material never changes its code.

### 4.3 Tamper-Evident Audit Chain
Every database update writes to `audit_log` within the same transaction:
- A database trigger takes a transaction advisory lock (`pg_advisory_xact_lock(727001)`).
- It reads the previous entry's hash.
- It computes: `this_hash = sha256(prev_hash || row_data)`.
- Updates, deletes, and truncates are blocked by triggers for all database roles.

---

## 5. Development Standards for Every Folder

Whenever you create a new directory in this repository, follow these rules:
1. **80% ASD-STE100 (Simplified Technical English):** Keep sentences short. Use simple words. Avoid ambiguity.
2. **Include a `README.md` with 5 Core Sections:**
   - **Purpose:** What the folder does.
   - **Theory:** How the underlying algorithms or concepts work.
   - **File Index:** Detailed summary of every file in the folder.
   - **Manual Testing Guide:** Exact commands to test the code from the command line.
   - **Related Documentation:** Links to parent, sibling, or dependent `README.md` files.

---

## 6. How to Run Baseline Tests Manually

Run all automated unit and integration tests using `uv`:

```powershell
# Run full repository test suite (53 tests)
uv run pytest tests/ -v

# Run linting check
uv run ruff check .

# Run complete quality gate (lint + tests)
make check
```
