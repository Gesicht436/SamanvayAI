---
name: samanvay-safety-review
description: Safety review checklist for any change to matching, tiering, extraction, document intake, MTC handling, lots or the audit log in the Samanvay material-code project, based on invariants S1 to S15 (no wrong merges, fail closed, identity is not substitution). Use this skill whenever reviewing or writing code that links, merges or compares materials, assigns a tier, uses a similarity score or ML model, sets a lot or MTC status, or changes approval and audit logic, and before declaring a task done in those areas, even if the user only says "review this" or "does this look right".
---

# Samanvay safety review

The project exists to prevent one failure: two materials that are not the same get linked under one national code (a Class 150 valve filed as a Class 300, an Ex Group I motor as Group II). A false merge in a refinery can hurt people. Missing a duplicate only costs money. The review below keeps every change biased toward the cheap error.

## How to review

1. Read the diff and list which areas it touches (matching, extraction, tiering, documents, MTC, lots, audit, security).
2. For each area, walk the matching section of the checklist. Quote the line of code that satisfies or violates each item.
3. Report findings as: **Violation** (breaks an invariant, must fix), **Risk** (could break it under some input), **Note**. Give a concrete failing input for every violation.
4. Check that a test exists for each invariant the change touches. If not, write the test case in the report. A property test that is skipped counts as absent.

## Checklist by area

**Tiering and matching** (S1 to S4, S9, S13, S14)
- Tier 1 requires every HARD and REQUIRED attribute present and equal on both sides, no extraction flags, no `PARTIAL_BLOCK` or `CATEGORY_UNCERTAIN`.
- Changing exactly one HARD attribute can never produce Tier 1, and shuffling input key order never changes the outcome.
- A similarity score, embedding distance or ML probability can lower a tier but never raise a gated item to Tier 1.
- In OEM part number and drawing identity modes, text similarity alone never gives Tier 1; for drawings, a revision difference is never better than Tier 2.
- Identity is not substitution: a higher class or better metallurgy may be an acceptable substitute, never an identical item.

**Extraction** (S2, S5, S11, S12)
- Invalid or conflicting values are `None` plus a flag, never a guess.
- A HARD attribute from OCR text below the confidence threshold becomes `None` with `LOW_OCR_CONFIDENCE`.
- Statutory attributes (IBR certificate, mine-equipment approval, Ex approval) are never inferred from free text alone and never taken from the LLM extractor alone.
- Ex Group I and II are never equal or substitutes; for Group I, an absent `gas_group` or `t_class` is not "missing".

**Documents** (S10)
- A duplicate document warns or blocks and never merges silently. File hash and invoice key are checked before parsing results are stored.

**MTC** (S15)
- No `CONFORMS` against an unverified reference row. The result for an unverified reference is `UNVERIFIED_REFERENCE`.
- A derived value (CE, PREN) is computed only when every input element is present; a missing element is never treated as zero.
- A lot becomes MTC-verified only by `CONFORMS` plus a heat or batch number match.

**Lots** (S6 to S8)
- An expired lot, or unknown expiry where one is required, is never GREEN, never eligible for Stream A and never auto-issued.
- A usage-based lot without usage events is never GREEN. Adding usage never raises remaining life. Risk never improves as time advances.
- Clock access goes through the injectable clock so tests can control time.

**Governance and security**
- The proposer and approver differ, and the checker holds the domain tag for safety-critical subcategories.
- The audit write happens in the same transaction as the change, and nothing can update or delete audit rows.
- Row-level security fails safe: an unset organisation or role sees nothing.
- No secrets in code, compose files or examples; no organisation identifiers in metric labels or logs.

## Language that must not appear in code, UI strings or docs

"Zero false merge", "statutory pricing formula", "meets statutory requirements", "auto-conforms". Report observed rates with confidence intervals instead.

## Finding unsafe patterns quickly

```bash
python scripts/scan_tier1.py <repo-root>
```

It lists every place where code assigns or returns Tier 1 outside the allowed tiering module, so a reviewer can check each one. It is a pointer for review, not a proof.
